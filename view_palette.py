#!/usr/bin/env python
# encoding: utf-8

import argparse

import numpy as np


def palette_to_image(palette):
    from PIL import Image

    WIDTH = 180
    HEIGHT_SEGMENT = 20
    img = Image.new("RGB", (WIDTH, HEIGHT_SEGMENT * len(palette)), "black")
    pixels = img.load()
    for i, color in enumerate(palette):
        if isinstance(color, int):
            b = (color >> 0) % 256
            g = (color >> 8) % 256
            r = (color >> 16) % 256
            color = (r, g, b)
        elif isinstance(color, np.ndarray):
            color = tuple(int(round(k * 255)) for k in color)
        for x in range(WIDTH):
            for y in range(HEIGHT_SEGMENT):
                pixels[x, y + i * HEIGHT_SEGMENT] = color
    return img


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""
    View a palette stored in a given file. The script requires PIL (Python
    Imaging Library).
    """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("palette", type=argparse.FileType("r"), help="palette filename")
    parser.add_argument("--save", type=str, help="save as a PNG file")
    args = parser.parse_args()

    palette = list()
    for line in args.palette.readlines():
        rgb = [int(c) for c in line.strip().split(",")]
        palette.append((rgb[0], rgb[1], rgb[2]))

    img = palette_to_image(palette)
    if args.save:
        img.save(args.save)
    else:
        img.show()
