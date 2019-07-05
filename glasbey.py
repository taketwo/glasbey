#!/usr/bin/env python
# encoding: utf-8

import os
import sys
import ast
import argparse

import numpy as np
from colorspacious import cspace_convert

try:
    # this works if you import Glasbey
    from .view_palette import palette_to_image
except ImportError:
    # this works if you run __main__() function
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


class Glasbey:
    def __init__(self,
                 base_palette=None,
                 overwrite_base_palette: bool = False,
                 no_black: bool = False,
                 lightness_range=None,
                 chroma_range=None,
                 hue_range=None):
        # Constants
        self.MAX = 256
        self.NUM_COLORS = self.MAX * self.MAX * self.MAX
        self.LUT = os.path.dirname(os.path.realpath(__file__)) + "/rgb_cam02ucs_lut.npz"

        self.overwrite_base_palette = overwrite_base_palette

        # Check input
        if type(base_palette) == str:
            assert os.path.isfile(base_palette), "file does not exist: {}".format(base_palette)
        elif type(base_palette) == list:
            assert self.check_validity_rbg_palette(base_palette), "Base palette must be in this format: [(255,255,255), ...]"
            assert not self.overwrite_base_palette, "base_palette is no file, cannot overwrite it!"
        else:
            assert not self.overwrite_base_palette, "no base_palette specified, cannot overwrite it!"

        # Load colors
        self.colors = self.load_or_generate_color_table()

        # Initialize base palette
        if type(base_palette) == str:
            self.base_palette = base_palette
            self.palette = self.load_palette(base_palette)
            self.palette = [self.colors[i, :] for i in self.palette]
        elif type(base_palette) == list and len(base_palette) > 0:
            self.palette = [(rgb[0] * 256 + rgb[1]) * 256 + rgb[2] for rgb in base_palette]
            self.palette = [self.colors[i, :] for i in self.palette]
        else:
            self.palette = [self.colors[-1, :]]  # white

        assert self.check_validity_internal_palette(), "Internal error during __init__: self.palette is poorly formatted."

        # Update self.colors
        # Exclude greys (values with low Chroma in JCh) and set lightness range,
        if lightness_range is not None:
            jch = cspace_convert(self.colors, "CAM02-UCS", "JCh")
            self.colors = self.colors[
                          (jch[:, 0] >= lightness_range[0]) & (jch[:, 0] <= lightness_range[1]), :
                          ]
        if chroma_range is not None:
            jch = cspace_convert(self.colors, "CAM02-UCS", "JCh")
            self.colors = self.colors[
                          (jch[:, 1] >= chroma_range[0]) & (jch[:, 1] <= chroma_range[1]), :
                          ]
        if hue_range is not None:
            jch = cspace_convert(self.colors, "CAM02-UCS", "JCh")
            if hue_range[0] > hue_range[1]:
                self.colors = self.colors[
                              (jch[:, 2] >= hue_range[0]) | (jch[:, 2] <= hue_range[1]), :
                              ]
            else:
                self.colors = self.colors[
                              (jch[:, 2] >= hue_range[0]) & (jch[:, 2] <= hue_range[1]), :
                              ]
        # Exclude colors that are close to black
        if no_black:
            MIN_DISTANCE_TO_BLACK = 35
            d = np.linalg.norm((self.colors - self.colors[0, :]), axis=1)
            self.colors = self.colors[d > MIN_DISTANCE_TO_BLACK, :]

    def generate_palette(self, size):
        """
        Return palette in sRGB1 format.

        If the palette isn't long enough, new entries are generated.
        """
        if size <= len(self.palette):
            return cspace_convert(self.palette[0:size], "CAM02-UCS", "sRGB1")

        # Initialize distances array
        num_colors = self.colors.shape[0]
        distances = np.ones(shape=(num_colors, 1)) * 1000

        # A function to recompute minimum distances from palette to all colors
        def update_distances(colors, color):
            d = np.linalg.norm((colors - color), axis=1)
            np.minimum(distances, d.reshape(distances.shape), distances)

        # Build progress bar
        widgets = ["Generating palette: ", Percentage(), " ", Bar(), " ", ETA()]
        pbar = ProgressBar(widgets=widgets, maxval=size).start()
        # Update distances for the colors that are already in the palette
        for i in range(len(self.palette) - 1):
            update_distances(self.colors, self.palette[i])
            pbar.update(i)
        # Iteratively build palette
        while len(self.palette) < size:
            update_distances(self.colors, self.palette[-1])
            self.palette.append(self.colors[np.argmax(distances), :])
            pbar.update(len(self.palette))
        pbar.finish()

        assert self.check_validity_internal_palette(), "Internal error during extend_palette: self.palette is poorly formatted."

        if self.overwrite_base_palette:
            self.save_palette(palette=self.palette, path=self.base_palette, format="byte", overwrite=True)

        return cspace_convert(self.palette[0:size], "CAM02-UCS", "sRGB1")

    def load_or_generate_color_table(self):
        # Load or generate RGB to CAM02-UCS color lookup table
        try:
            colors = np.load(self.LUT)["lut"]
            # Sanity check
            assert colors.shape == (self.NUM_COLORS, 3)
        except:
            colors = self.generate_color_table()
            np.savez_compressed(self.LUT, lut=colors)
        return colors

    def generate_color_table(self):
        """
        Generate a lookup table with all possible RGB colors, encoded in
        perceptually uniform CAM02-UCS color space.

        Table rows correspond to individual RGB colors, columns correspond to J',
        a', and b' components. The table is stored as a NumPy array.
        """

        widgets = ["Generating color table: ", Percentage(), " ", Bar(), " ", ETA()]
        pbar = ProgressBar(widgets=widgets, maxval=(self.MAX * self.MAX)).start()

        i = 0
        colors = np.empty(shape=(self.NUM_COLORS, 3), dtype=float)
        for r in range(self.MAX):
            for g in range(self.MAX):
                d = i * self.MAX
                for b in range(self.MAX):
                    colors[d + b, :] = (r, g, b)
                colors[d:d + self.MAX] = cspace_convert(
                    colors[d:d + self.MAX], "sRGB255", "CAM02-UCS"
                )
                pbar.update(i)
                i += 1
        pbar.finish()
        return colors

    @staticmethod
    def load_palette(path):
        """
        Expected format: sRGB255
        """
        assert os.path.isfile(path)
        palette = list()
        with open(path, 'r') as file:
            for line in file:
                rgb = [int(c) for c in line.strip().split(",")]
                palette.append((rgb[0] * 256 + rgb[1]) * 256 + rgb[2])
        return palette

    @staticmethod
    def save_palette(palette, path: str, format: str = "byte", overwrite: bool = False):
        """
        Output format examples (white):
            * byte:  255,255,255  (sRGB255)
            * float: 1.000000,1.000000,1.000000
        """
        if not overwrite:
            assert not os.path.isfile(path)

        with open(path, 'w') as file:
            if format.lower() == "byte":
                for color in palette:
                    rgb255 = tuple(int(round(k * 255)) for k in color)
                    file.write("{},{},{}\n".format(*rgb255))
            elif format.lower() == "float":
                for color in palette:
                    file.write("{:.6f},{:.6f},{:.6f}\n".format(*(abs(k) for k in color)))
            else:
                raise ValueError("Format doesn't match. Choose between 'byte' and 'float'")

    def check_validity_internal_palette(self):
        if type(self.palette) != list:
            return False
        for color in self.palette:
            if len(color) != 3 or type(color) != np.ndarray:
                return False
        return True

    @staticmethod
    def check_validity_rbg_palette(palette):
        if type(palette) != list:
            return False
        for color in palette:
            if len(color) != 3 or type(color) != tuple:
                return False
            if not 0 <= color[0] <= 255 and 0 <= color[1] <= 255 and 0 <= color[2] <= 255:
                return False

        return True

    @staticmethod
    def convert_palette_to_rgb(palette):
        """
        Convert palette from sRGB1 to sRGB255.
        """
        return [tuple(int(round(k * 255)) for k in color) for color in palette]

    @staticmethod
    def view_palette(palette):
        """
        Show palette in imagemagick window.

        Expected format: sRGB1 or sRGB255
        """
        img = palette_to_image(palette)
        img.show()


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
    parser.add_argument("--hue-range", type=ast.literal_eval,
                        help="set start and end for hue (e.g. 315,45)")
    parser.add_argument("--view", action="store_true",
                        help="view generated palette")
    parser.add_argument("--format", default="byte", choices=["byte", "float"],
                        help="output format")
    parser.add_argument("size", type=int,
                        help="number of colors in the palette")
    parser.add_argument("output", type=argparse.FileType("w"),
                        help="output palette filename")
    args = parser.parse_args()

    if args.format not in ["byte", "float"]:
        sys.exit('Invalid output format "{}"'.format(args.format))

    gb = Glasbey(base_palette=args.base_palette.name,
                 overwrite_base_palette=False,
                 no_black=args.no_black,
                 lightness_range=args.lightness_range,
                 chroma_range=args.chroma_range,
                 hue_range=args.hue_range)

    new_palette = gb.generate_palette(size=args.size)
    assert len(new_palette) == args.size

    gb.save_palette(new_palette, args.output.name, args.format, overwrite=True)

    if args.view:
        gb.view_palette(new_palette)
