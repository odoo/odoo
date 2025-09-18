from collections.abc import Sequence
from hashlib import sha512


def get_saturation(rgb: Sequence[int]) -> float:
    """Return the saturation (HSL format) of a given RGB color.

    :param rgb: RGB tuple or list with values 0-255
    :returns: Saturation value between 0 and 1

    Example::

        >>> get_saturation((255, 0, 0))  # Pure red
        1.0
        >>> get_saturation((128, 128, 128))  # Gray
        0.0
    """
    c_max = max(rgb) / 255
    c_min = min(rgb) / 255
    d = c_max - c_min
    return 0 if d == 0 else d / (1 - abs(c_max + c_min - 1))


def get_lightness(rgb: Sequence[int]) -> float:
    """Return the lightness (HSL format) of a given RGB color.

    :param rgb: RGB tuple or list with values 0-255
    :returns: Lightness value between 0 and 1

    Example::

        >>> get_lightness((255, 255, 255))  # White
        1.0
        >>> get_lightness((0, 0, 0))  # Black
        0.0
        >>> get_lightness((128, 128, 128))  # Middle gray
        0.5019607843137255
    """
    return (max(rgb) + min(rgb)) / 2 / 255


def hex_to_rgb(hx: str) -> tuple[int, int, int]:
    """Convert a hexadecimal color string to an RGB tuple.

    :param hx: Hexadecimal color string starting with '#' (e.g., '#FF0000')
    :returns: RGB tuple with values 0-255

    Example::

        >>> hex_to_rgb('#FF0000')
        (255, 0, 0)
        >>> hex_to_rgb('#00FF00')
        (0, 255, 0)
    """
    return tuple(int(hx[i : i + 2], 16) for i in range(1, 6, 2))  # type: ignore


def rgb_to_hex(rgb: Sequence[int]) -> str:
    """Convert an RGB tuple or list to a hexadecimal color string.

    :param rgb: RGB tuple or list with values 0-255
    :returns: Hexadecimal color string starting with '#'

    Example::

        >>> rgb_to_hex((255, 0, 0))
        '#ff0000'
        >>> rgb_to_hex((0, 255, 0))
        '#00ff00'
    """
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def hsl_from_seed(seed: str) -> str:
    """Generate a deterministic HSL color string from a seed string.

    Hashes the seed with SHA-512 and derives hue, saturation, and lightness
    values. The result is colorful but not too flashy, and not too bright or
    dark — suitable for avatar background colors.

    :param seed: Arbitrary string used to generate the color
    :returns: HSL color string, e.g. ``'hsl(214, 55%, 45%)'``

    Example::

        >>> hsl_from_seed('Alice')  # deterministic
        'hsl(214, 55%, 45%)'
    """
    hashed_seed = sha512(seed.encode()).hexdigest()
    # full range of colors, in degree
    hue = int(hashed_seed[0:2], 16) * 360 / 255
    # colorful result but not too flashy, in percent
    sat = int(hashed_seed[2:4], 16) * ((70 - 40) / 255) + 40
    # not too bright and not too dark, in percent
    lig = 45
    return f"hsl({hue:.0f}, {sat:.0f}%, {lig:.0f}%)"
