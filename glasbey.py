#!/usr/bin/env python
# encoding: utf-8

import sys
import ast
import argparse

import numpy as np
from colorspacious import cspace_convert

from view_palette import palette_to_image


try:
    from progressbar import Bar, ETA, Percentage, ProgressBar
except ImportError:

    class Bar:
        pass

    class ETA:
        pass

    class Percentage:
        pass

    class ProgressBar:
        def __init__(self, **kwargs):
            pass

        def start(self):
            return self

        def update(self, i):
            pass

        def finish(self):
            pass


MAX = 256
NUM_COLORS = MAX * MAX * MAX


def generate_color_table():
    """
    Generate a lookup table with all possible RGB colors, encoded in
    perceptually uniform CAM02-UCS color space.

    Table rows correspond to individual RGB colors, columns correspond to J',
    a', and b' components. The table is stored as a NumPy array.
    """

    widgets = ["Generating color table: ", Percentage(), " ", Bar(), " ", ETA()]
    pbar = ProgressBar(widgets=widgets, maxval=(MAX * MAX)).start()

    i = 0
    colors = np.empty(shape=(NUM_COLORS, 3), dtype=float)
    for r in range(MAX):
        for g in range(MAX):
            d = i * MAX
            for b in range(MAX):
                colors[d + b, :] = (r, g, b)
            colors[d:d + MAX] = cspace_convert(
                colors[d:d + MAX], "sRGB255", "CAM02-UCS"
            )
            pbar.update(i)
            i += 1
    pbar.finish()
    return colors


def generate_palette(
    colors,
    size,
    base=None,
    no_black=False,
    lightness_range=None,
    chroma_range=None,
    hue_range=None,
):
    # Initialize palette with given base or white color
    if base:
        palette = [colors[i, :] for i in base]
    else:
        palette = [colors[-1, :]]  # white
    # Exclude greys (values with low Chroma in JCh) and set lightness range,
    if lightness_range is not None:
        jch = cspace_convert(colors, "CAM02-UCS", "JCh")
        colors = colors[
            (jch[:, 0] >= lightness_range[0]) & (jch[:, 0] <= lightness_range[1]), :
        ]
    if chroma_range is not None:
        jch = cspace_convert(colors, "CAM02-UCS", "JCh")
        colors = colors[
            (jch[:, 1] >= chroma_range[0]) & (jch[:, 1] <= chroma_range[1]), :
        ]
    if hue_range is not None:
        jch = cspace_convert(colors, "CAM02-UCS", "JCh")
        if hue_range[0] > hue_range[1]:
            colors = colors[
                (jch[:, 2] >= hue_range[0]) | (jch[:, 2] <= hue_range[1]), :
            ]
        else:
            colors = colors[
                (jch[:, 2] >= hue_range[0]) & (jch[:, 2] <= hue_range[1]), :
            ]
    # Exclude colors that are close to black
    if no_black:
        MIN_DISTANCE_TO_BLACK = 35
        d = np.linalg.norm((colors - colors[0, :]), axis=1)
        colors = colors[d > MIN_DISTANCE_TO_BLACK, :]
    # Initialize distances array
    num_colors = colors.shape[0]
    distances = np.ones(shape=(num_colors, 1)) * 1000
    # A function to recompute minimum distances from palette to all colors
    def update_distances(colors, color):
        d = np.linalg.norm((colors - color), axis=1)
        np.minimum(distances, d.reshape(distances.shape), distances)

    # Build progress bar
    widgets = ["Generating palette: ", Percentage(), " ", Bar(), " ", ETA()]
    pbar = ProgressBar(widgets=widgets, maxval=size).start()
    # Update distances for the colors that are already in the palette
    for i in range(len(palette) - 1):
        update_distances(colors, palette[i])
        pbar.update(i)
    # Iteratively build palette
    while len(palette) < size:
        update_distances(colors, palette[-1])
        palette.append(colors[np.argmax(distances), :])
        pbar.update(len(palette))
    pbar.finish()
    return cspace_convert(palette, "CAM02-UCS", "sRGB1")


def load_palette(f):
    palette = list()
    for line in f.readlines():
        rgb = [int(c) for c in line.strip().split(",")]
        palette.append((rgb[0] * 256 + rgb[1]) * 256 + rgb[2])
    return palette


def save_palette(palette, f, fmt):
    if fmt == "byte":
        for color in palette:
            rgb255 = tuple(int(round(k * 255)) for k in color)
            f.write("{},{},{}\n".format(*rgb255))
    else:
        for color in palette:
            f.write("{:.6f},{:.6f},{:.6f}\n".format(*(abs(k) for k in color)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""
    Generate a palette with maximally disticts colors using the sequential
    method of Glasbey et al.¹

    (Dis)similarity between colors is computed in the state-of-the-art
    perceptually uniform color space CAM02-UCS.²

    This script needs an RGB to CAM02-UCS color lookup table. Generation of
    this table is a time-consuming process, therefore the first run of this
    script will take some time. The generated table will be stored in the
    working directory of the script and automatically used in next invocations
    of the script. Note that the approximate size of the table is 363 Mb.

    The palette generation method allows the user to supply a base palette. The
    output palette will begin with the colors from the supplied set. If no base
    palette is given, then white will be used as the first base color. The base
    palette should be given as a text file where each line contains a color
    description in RGB255 format with components separated with commas. (See
    files in the 'palettes/' folder for an example.)

    If having black (and colors close to black) is undesired, then `--no-black`
    option may be used to prevent the algorithm from inserting such colors into
    the palette. In addition to that, the range of colors considered for
    inclusion in the palette can be limited by lightness, chroma, or hue.

    ¹) Glasbey, C., van der Heijden, G., Toh, V. F. K. and Gray, A. (2007),
       Colour Displays for Categorical Images.
       Color Research and Application, 304-309

    ²) Luo, M. R., Cui, G. and Li, C. (2006),
       Uniform Colour Spaces Based on CIECAM02 Colour Appearance Model.
       Color Research and Application, 320–330
    """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--base-palette", type=argparse.FileType("r"), help="file with base palette"
    )
    parser.add_argument(
        "--no-black", action="store_true", help="avoid black and similar colors"
    )
    parser.add_argument(
        "--lightness-range",
        type=ast.literal_eval,
        help="set min and max for lightness (e.g. 0,90)",
    )
    parser.add_argument(
        "--chroma-range",
        type=ast.literal_eval,
        help="set min and max for chroma (e.g. 10,100)",
    )
    parser.add_argument(
        "--hue-range",
        type=ast.literal_eval,
        help="set start and end for hue (e.g. 315,45)",
    )
    parser.add_argument("--view", action="store_true", help="view generated palette")
    parser.add_argument(
        "--format", default="byte", choices=["byte", "float"], help="output format"
    )
    parser.add_argument("size", type=int, help="number of colors in the palette")
    parser.add_argument(
        "output", type=argparse.FileType("w"), help="output palette filename"
    )
    args = parser.parse_args()

    if args.format not in ["byte", "float"]:
        sys.exit('Invalid output format "{}"'.format(args.format))

    # Load base palette
    base = load_palette(args.base_palette) if args.base_palette else None

    # Load or generate RGB to CAM02-UCS color lookup table
    LUT = "rgb_cam02ucs_lut.npz"
    try:
        colors = np.load(LUT)["lut"]
        # Sanity check
        assert colors.shape == (NUM_COLORS, 3)
    except:
        colors = generate_color_table()
        np.savez_compressed(LUT, lut=colors)

    palette = generate_palette(
        colors,
        args.size,
        base,
        no_black=args.no_black,
        lightness_range=args.lightness_range,
        chroma_range=args.chroma_range,
        hue_range=args.hue_range,
    )
    save_palette(palette, args.output, args.format)

    if args.view:
        img = palette_to_image(palette)
        img.show()
