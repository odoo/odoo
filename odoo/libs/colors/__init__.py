from .conversions import (
    get_brightness,
    get_palette_color,
    get_saturation,
    get_lightness,
    hex_to_rgb,
    lighten_hex,
    rgb_to_hex,
    get_hsl_from_seed,
)
from .terminal import (
    BLACK,
    BLUE,
    COLOR_PATTERN,
    COLOR_SEQ,
    CYAN,
    DEFAULT,
    GREEN,
    MAGENTA,
    RED,
    RESET_SEQ,
    WHITE,
    YELLOW,
    colorize,
)

TAG_COLORS = (
    "#FFFFFF",
    "#F06050",
    "#F4A460",
    "#F7CD1F",
    "#6CC1ED",
    "#814968",
    "#EB7E7F",
    "#2C8397",
    "#475577",
    "#D6145F",
    "#30C381",
    "#9365B8",
)
TAG_COLOR_INDICES = tuple(range(len(TAG_COLORS)))

PLANNING_COLORS = (
    "#008784",
    "#EE4B39",
    "#F29648",
    "#F4C609",
    "#55B7EA",
    "#71405B",
    "#E86869",
    "#008784",
    "#267283",
    "#BF1255",
    "#2BAF73",
    "#8754B0",
)

LEAVE_REPORT_COLORS = (
    "lightgrey",
    "tomato",
    "sandybrown",
    "khaki",
    "skyblue",
    "dimgrey",
    "lightcoral",
    "steelblue",
    "darkslateblue",
    "crimson",
    "mediumseagreen",
    "mediumpurple",
)


ROUTE_COLORS = (
    "#FFA500",
    "#800080",
    "#228B22",
    "#008B8B",
    "#4682B4",
    "#FF0000",
    "#32CD32",
)

GPS_TRAIL_COLORS = (
    "#3366FF",
    "#FF6633",
    "#33CC33",
    "#CC33FF",
    "#FFCC00",
    "#00CCCC",
    "#FF3366",
    "#6633FF",
    "#33FFCC",
    "#FF9933",
    "#9933FF",
    "#33FF66",
)

GEO_TRAIL_COLORS = (
    "#E4572E",
    "#17BEBB",
    "#FFC914",
    "#2E294E",
    "#76B041",
    "#A053A1",
    "#0B7A75",
)

__all__ = [
    "BLACK",
    "BLUE",
    "COLOR_PATTERN",
    "COLOR_SEQ",
    "CYAN",
    "DEFAULT",
    "GEO_TRAIL_COLORS",
    "GPS_TRAIL_COLORS",
    "GREEN",
    "LEAVE_REPORT_COLORS",
    "MAGENTA",
    "PLANNING_COLORS",
    "RED",
    "RESET_SEQ",
    "ROUTE_COLORS",
    "TAG_COLORS",
    "TAG_COLOR_INDICES",
    "WHITE",
    "YELLOW",
    "colorize",
    "get_brightness",
    "get_hsl_from_seed",
    "get_lightness",
    "get_palette_color",
    "get_saturation",
    "hex_to_rgb",
    "lighten_hex",
    "rgb_to_hex",
]
