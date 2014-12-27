#!/usr/bin/env python
# encoding: utf-8

import argparse
import numpy as np
from colormath.color_objects import LabColor, sRGBColor
from colormath.color_conversions import convert_color
from view_palette import palette_to_image


try:
    from progressbar import Bar, ETA, Percentage, ProgressBar
except ImportError:
    class Bar: pass
    class ETA: pass
    class Percentage: pass
    class ProgressBar:
        def __init__(self, **kwargs): pass
        def start(self): return self
        def update(self, i): pass
        def finish(self): pass


MAX = 256
NUM_COLORS = MAX * MAX * MAX


def lab_from_rgb(r, g, b):
    rgb = sRGBColor(r, g, b, is_upscaled=True)
    lab = convert_color(rgb, LabColor, target_illuminant='d50')
    return lab.get_value_tuple()


def rgb_from_lab(lab):
    """
    Convert a color from CIELab space into RGB space. The RGB components are
    upscaled (in [0..255] interval).

    Parameters
    ----------
    lab : list, tuple, or numpy array
        A 3-element array with L, a, and b components of the color.
    """
    lab = LabColor(lab[0], lab[1], lab[2])
    rgb = convert_color(lab, sRGBColor, target_illuminant='d50')
    return tuple(round(k * 255) for k in rgb.get_value_tuple())


def generate_color_table():
    """
    Generate a lookup table with all possible RGB colors, encoded in CIE Lab
    color space.

    Table rows correspond to colors, and columns correspond to L, a, and b
    components. The table is stored as a NumPy array.
    """
    i = 0
    MAX = 256
    NUM_COLORS = MAX * MAX * MAX
    colors = np.empty(shape=(NUM_COLORS, 3), dtype=float)

    widgets = ['Generating color table: ',
               Percentage(), ' ',
               Bar(), ' ',
               ETA()]
    pbar = ProgressBar(widgets=widgets, maxval=NUM_COLORS).start()

    for r in range(MAX):
        for g in range(MAX):
            for b in range(MAX):
                colors[i, :] = lab_from_rgb(r, g, b)
                pbar.update(i)
                i += 1
    pbar.finish()
    return colors


def generate_palette(colors, size, base=None, no_black=False):
    # Initialize palette with given base or white color
    if base:
        palette = [colors[i, :] for i in base]
    else:
        palette = [colors[-1, :]]  # white
    # Exclude colors that are close to black
    if no_black:
        d = np.linalg.norm((colors - colors[0, :]), axis=1)
        colors = colors[d > 45, :]
    # Initialize distances array
    num_colors = colors.shape[0]
    distances = np.ones(shape=(num_colors, 1)) * 1000
    # A function to recompute minimum distances from palette to all colors
    def update_distances(colors, color):
        d = np.linalg.norm((colors - color), axis=1)
        np.minimum(distances, d.reshape(distances.shape), distances)
    # Build progress bar
    widgets = ['Generating palette: ',
               Percentage(), ' ',
               Bar(), ' ',
               ETA()]
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
    print(np.max(distances))
    return [rgb_from_lab(c) for c in palette]


def load_palette(f):
    palette = list()
    for line in f.readlines():
        rgb = [int(c) for c in line.strip().split(',')]
        palette.append((rgb[0] * 256 + rgb[1]) * 256 + rgb[2])
    return palette


def save_palette(palette, f):
    for color in palette:
        f.write('{0},{1},{2}\n'.format(*color))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''
    Generate a color palette using the sequential method of Glasbey et al.¹

    This script needs an RGB to Lab color lookup table. Generation of this
    table is a time-consuming process, therefore the first run of this script
    will take some time. The generated table will be stored and automatically
    used in next invocations of the script. Note that the approximate size of
    the table is 363 Mb.

    The palette generation method allows the user to supply a base palette. The
    output palette will begin with the colors from the supplied set. If no base
    palette is given, then white will be used as the first base color. The base
    palette should be given as a text file where each line contains a color
    description in RGB format with components separated with commas. (See files
    in the 'palettes/' folder for an example).

    If having black (and colors close to black) is undesired, then `--no-black`
    option may be used to prevent the algorithm from inserting such colors into
    the palette.

    ¹) Glasbey, C., van der Heijden, G., Toh, V. F. K. and Gray, A. (2007),
       Colour Displays for Categorical Images.
       Color Research and Application, 32: 304-309
    ''', formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--base-palette', type=argparse.FileType('r'),
                        help='file with base palette')
    parser.add_argument('--no-black', action='store_true',
                        help='avoid black and similar colors')
    parser.add_argument('--view', action='store_true',
                        help='view generated palette')
    parser.add_argument('size', type=int,
                        help='number of colors in the palette')
    parser.add_argument('output', type=argparse.FileType('w'),
                        help='output palette filename')
    args = parser.parse_args()

    # Load base palette
    base = load_palette(args.base_palette) if args.base_palette else None

    # Load or generate RGB to Lab color lookup table
    LUT = 'rgb_lab_lut.npz'
    try:
        colors = np.load(LUT)['lut']
        # Sanity check
        assert colors.shape == (NUM_COLORS, 3)
    except:
        colors = generate_color_table()
        np.savez_compressed(LUT, lut=colors)

    palette = generate_palette(colors, args.size, base, no_black=args.no_black)
    save_palette(palette, args.output)

    if args.view:
        img = palette_to_image(palette)
        img.show()
