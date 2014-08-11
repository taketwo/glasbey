When visualizing categorical data we often want to encode each category with a
distinct color. The set of colors may be generated randomly, however more
visually pleasing results can be achieved if special care is taken to generate
a maximally distinct set of colors.

This repository contains an implementation of a method proposed by Glasbey et
al. [1] that is capable of identifying such a set.

Requirements
------------

Mandatory:

* [`python-colormath`](https://github.com/gtaylor/python-colormath)

Optional:

* [`python-progressbar`](https://code.google.com/p/python-progressbar/) to show
  a progress bar during palette generation
* [`python-pillow`](https://github.com/python-pillow/Pillow) to visualize
  generated palettes

Usage
-----

```
usage: glasbey.py [-h] [--base-palette BASE_PALETTE] [--no-black] [--view]
                  size output

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

positional arguments:
  size                  number of colors in the palette
  output                output palette filename

optional arguments:
  -h, --help            show this help message and exit
  --base-palette BASE_PALETTE
                        file with base palette
  --no-black            avoid black and similar colors
  --view                view generated palette
```

References
----------

1) Glasbey, C., van der Heijden, G., Toh, V. F. K. and Gray, A. (2007),
   [Colour Displays for Categorical Images](http://onlinelibrary.wiley.com/doi/10.1002/col.20327/abstract).
   Color Research and Application, 32: 304-309
