# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""The color math the website's colors are compiled with.

The SCSS compile derives many colors from the ones the user picks: a readable
text color on a background, a link darkened until it is readable, the hover
and active colors of buttons... Some of them can be written in CSS
(`color-mix()`); the others need code: they branch on the colors (contrast
decisions) or use HSL adjustments. This module computes those the same way as
the SCSS functions (Bootstrap's, web's and html_editor's), including libsass'
rounding, so that a preview matches what the compile gives on save.

A color is an `(r, g, b, a)` tuple, the channels between 0 and 255 (not
necessarily integers: libsass does not round HSL adjustments), alpha between 0
and 1.
"""
import math
import re

WHITE = (255, 255, 255, 1)
BLACK = (0, 0, 0, 1)
TRANSPARENT = (0, 0, 0, 0)

_HEX_RE = re.compile(r'#([0-9a-f]{3,8})', re.IGNORECASE)
_RGB_RE = re.compile(r'rgba?\(([^)]*)\)', re.IGNORECASE)


def parse_color(value):
    """Parse a hexadecimal, `rgb()` or `rgba()` color.

    :param str value:
    :rtype: tuple | None
    """
    value = (value or '').strip()
    if match := _HEX_RE.fullmatch(value):
        digits = match.group(1)
        if len(digits) in (3, 4):
            digits = ''.join(digit * 2 for digit in digits)
        if len(digits) not in (6, 8):
            return None
        channels = [int(digits[i:i + 2], 16) for i in range(0, len(digits), 2)]
        alpha = channels[3] / 255 if len(channels) == 4 else 1
        return (*channels[:3], alpha)
    if match := _RGB_RE.fullmatch(value):
        parts = [part for part in re.split(r'[\s,/]+', match.group(1)) if part]
        if len(parts) not in (3, 4):
            return None
        try:
            numbers = [float(part[:-1]) / 100 if part.endswith('%') else float(part) for part in parts]
        except ValueError:
            return None
        return (*numbers[:3], numbers[3] if len(numbers) == 4 else 1)
    return None


def format_color(color):
    """Format a color as CSS, channels rounded as libsass prints them."""
    r, g, b = (sass_round(channel) for channel in color[:3])
    alpha = color[3]
    if alpha >= 1:
        return f'#{r:02x}{g:02x}{b:02x}'
    return f'rgba({r}, {g}, {b}, {format_number(alpha)})'


def format_number(number):
    """A number as libsass prints it (8 decimals, trailing zeros removed)."""
    text = f'{number:.8f}'.rstrip('0').rstrip('.')
    return '0' if text == '-0' else text


def to_rgb(color):
    """Bootstrap's `to-rgb()`: the channels, comma-separated."""
    return ', '.join(format_number(channel) for channel in color[:3])


def sass_round(value):
    """libsass' `round()`: half up, with a tolerance at its precision (8)."""
    if math.fmod(value, 1) - 0.5 > -1e-9:
        return math.ceil(value)
    return math.floor(value)


# --- Sass and Bootstrap functions -------------------------------------------

def mix(color1, color2, weight=50):
    """Sass' `mix()` (weight in %), channels rounded as libsass does."""
    p = weight / 100
    w = p * 2 - 1
    a = color1[3] - color2[3]
    w1 = ((w if w * a == -1 else (w + a) / (1 + w * a)) + 1) / 2
    w2 = 1 - w1
    return (
        *(sass_round(c1 * w1 + c2 * w2) for c1, c2 in zip(color1[:3], color2[:3])),
        color1[3] * p + color2[3] * (1 - p),
    )


def tint_color(color, weight):
    return mix(WHITE, color, weight)


def shade_color(color, weight):
    return mix(BLACK, color, weight)


def opaque(background, foreground):
    """Bootstrap's `opaque()`: the foreground over the background."""
    return mix((*foreground[:3], 1), background, foreground[3] * 100)


def with_alpha(color, alpha):
    return (*color[:3], alpha)


def to_hsl(color):
    """`(h, s, l)` in degrees and percents, as libsass computes them."""
    r, g, b = (channel / 255 for channel in color[:3])
    high, low = max(r, g, b), min(r, g, b)
    delta = high - low
    lightness = (high + low) / 2
    hue = saturation = 0
    if abs(high - low) > 1e-10:
        saturation = delta / (high + low) if lightness < 0.5 else delta / (2 - high - low)
        if r == high:
            hue = (g - b) / delta + (6 if g < b else 0)
        elif g == high:
            hue = (b - r) / delta + 2
        else:
            hue = (r - g) / delta + 4
    return hue * 60, saturation * 100, lightness * 100


def from_hsl(hue, saturation, lightness, alpha=1):
    h = math.fmod(hue / 360, 1)
    h = h + 1 if h < 0 else h
    s = min(max(saturation / 100, 0), 1)
    lightness = min(max(lightness / 100, 0), 1)
    m2 = lightness * (s + 1) if lightness <= 0.5 else lightness + s - lightness * s
    m1 = lightness * 2 - m2

    def hue_to_rgb(value):
        value = math.fmod(value, 1)
        value = value + 1 if value < 0 else value
        if value * 6 < 1:
            return m1 + (m2 - m1) * value * 6
        if value * 2 < 1:
            return m2
        if value * 3 < 2:
            return m1 + (m2 - m1) * (2 / 3 - value) * 6
        return m1

    return (hue_to_rgb(h + 1 / 3) * 255, hue_to_rgb(h) * 255, hue_to_rgb(h - 1 / 3) * 255, alpha)


def adjust_lightness(color, amount):
    """Sass' `adjust-color($color, $lightness: amount)`; `darken()` is a
    negative amount, `lighten()` a positive one."""
    hue, saturation, lightness = to_hsl(color)
    return from_hsl(hue, saturation, min(100, max(0, lightness + amount)), color[3])


def lightness(color):
    return to_hsl(color)[2]


def _luminance_channel(value):
    if value / 255 < 0.04045:
        return value / 255 / 12.92
    # Bootstrap's `$_luminance-list` (4 digits), indexed by the channel: the
    # index of a fractional channel is floored.
    return round(((math.floor(value) / 255 + 0.055) / 1.055) ** 2.4, 4)


def luminance(color):
    """Bootstrap's `luminance()`."""
    r, g, b = (_luminance_channel(channel) for channel in color[:3])
    return r * 0.2126 + g * 0.7152 + b * 0.0722


def contrast_ratio(background, foreground):
    """Bootstrap's `contrast-ratio()`."""
    l1 = luminance(background)
    l2 = luminance(opaque(background, foreground))
    return (l1 + 0.05) / (l2 + 0.05) if l1 > l2 else (l2 + 0.05) / (l1 + 0.05)


def luma(color):
    """web's `luma()`, in percents."""
    r, g, b = color[:3]
    return (r * 0.299 + g * 0.587 + b * 0.114) / 255 * 100


def has_enough_contrast(color1, color2, threshold=500):
    """html_editor's `has-enough-contrast()`."""
    return sum(abs(c1 - c2) for c1, c2 in zip(color1[:3], color2[:3])) >= threshold


def increase_contrast(color1, color2):
    """html_editor's `increase-contrast()`: the color made lighter or darker,
    1% at a time (25% at most), until it contrasts enough with the other."""
    increment = -1 if luma(color1) < luma(color2) else 1
    color_lightness = lightness(color1)
    i = 0
    while 0.1 < color_lightness < 99.9 and i < 25 and not has_enough_contrast(color1, color2):
        color1 = adjust_lightness(color1, increment)
        color_lightness += increment
        i += 1
    return color1


class ColorContrast:
    """web's `color-contrast()` override, with the compile's constants: the
    first of light, dark, white and black that contrasts enough with the
    background (over the main background), else the one contrasting most."""

    def __init__(self, light, dark, main_background, min_ratio, white=WHITE, black=BLACK):
        self.light = light
        self.dark = dark
        self.main_background = main_background
        self.min_ratio = min_ratio
        self.white = white
        self.black = black

    def __call__(self, background, main_background=None, min_ratio=None):
        real_color = opaque(main_background or self.main_background, background)
        min_ratio = min_ratio or self.min_ratio
        max_ratio = 0
        max_ratio_color = None
        for color in (self.light, self.dark, self.white, self.black):
            ratio = contrast_ratio(real_color, color)
            if ratio > min_ratio:
                return color
            if ratio > max_ratio:
                max_ratio = ratio
                max_ratio_color = color
        return max_ratio_color

    def button_variant(self, background, border):
        """Bootstrap's `button-variant()` colors (with its default amounts)."""
        color = self(background)
        is_light = color == self.light
        hover_background = shade_color(background, 15) if is_light else tint_color(background, 15)
        active_background = shade_color(background, 20) if is_light else tint_color(background, 20)
        return {
            'color': color,
            'hover-color': self(hover_background),
            'hover-bg': hover_background,
            'hover-border-color': shade_color(border, 20) if is_light else tint_color(border, 10),
            'focus-shadow-rgb': mix(color, border, 15),
            'active-color': self(active_background),
            'active-bg': active_background,
            'active-border-color': shade_color(border, 25) if is_light else tint_color(border, 10),
            'disabled-color': color,
        }

    def button_outline_variant(self, color):
        """Bootstrap's `button-outline-variant()` colors that are not `color`."""
        return {
            'hover-color': self(color),
            'focus-shadow-rgb': color,
            'active-color': self(color),
        }


# --- The color system's computed values --------------------------------------

AREAS = (
    'menu', 'header-sales_one', 'header-sales_two', 'header-sales_three', 'header-sales_four',
    'footer', 'copyright', 'breadcrumb', 'portal-card',
)


def compute_colors(colors, user_keys=(), min_contrast_ratio=2.9, areas=None):
    """The colors the compile computes from the given ones (the custom
    properties of the same names it prints), for a preview of the colors.

    :param dict colors: CSS colors by name: the grays (`white`, `200`, `900`,
        `black`), the theme colors (`primary`...), and the colors of the color
        combinations that are set (their background always is).
    :param user_keys: the palette colors the user set (their links are not
        made readable, see html_editor's `auto-contrast()`)
    :param float min_contrast_ratio:
    :param dict areas: the color preset number of each area (`menu`,
        `footer`...), if any (their custom colors are in `colors`)
    :return: CSS values by custom property name (without `--`), and the
        theme gates computed from the colors (name: whether it's on)
    :rtype: tuple(dict, dict)
    """
    colors = {name: color for name, value in colors.items() if (color := parse_color(value))}
    contrast = ColorContrast(
        light=colors.get('white', WHITE),
        dark=colors.get('900', parse_color('#212529')),
        main_background=colors.get('o-cc1-bg', WHITE),
        min_ratio=min_contrast_ratio,
        white=colors.get('white', WHITE),
        black=colors.get('black', BLACK),
    )
    values = {}
    index = 1
    while f'o-cc{index}-bg' in colors:
        values.update(_compute_combination(f'o-cc{index}', colors, contrast, user_keys))
        index += 1
    values.update(_compute_root(colors, contrast, user_keys))
    area_values, gates = _compute_areas(colors, contrast, areas or {})
    values.update(area_values)
    return {
        name: to_rgb(value) if name.endswith('-rgb') else (format_color(value) if isinstance(value, tuple) else value)
        for name, value in values.items()
    }, gates


def _compute_areas(colors, contrast, areas):
    """The areas' values (see website's `o-after-bootstrap-root`)."""
    values = {}
    body_background = colors['o-cc1-bg']

    def area_color(area):
        preset = areas.get(area)
        return colors.get(f'{area}-custom') or (preset and colors.get(f'o-cc{preset}-bg'))

    footer = area_color('footer')
    for area in AREAS:
        custom = colors.get(f'{area}-custom')
        if custom and custom[3] > 0.3:
            background = (footer or TRANSPARENT) if area == 'copyright' else body_background
            values[f'{area}-custom-contrast'] = contrast(custom, main_background=background)
        elif custom:
            # Too translucent for a contrast: the area's text, its preset's
            # else its parent's (see `o-area-colors`).
            preset = str(areas.get(area) or '')
            values[f'{area}-custom-contrast'] = f'var(--o-cc{preset}-text)' if preset.isdigit() else 'currentColor'
    # The footer's scroll-to-top button.
    footer_fill = opaque(body_background, footer or TRANSPARENT)
    copyright_fill = opaque(footer_fill, area_color('copyright') or TRANSPARENT)
    footer_contrast = contrast(footer_fill, main_background=footer_fill)
    values['o-footer-scrolltop-bg'] = footer_fill
    values['o-footer-scrolltop-contrast'] = footer_contrast
    values['o-footer-scrolltop-color'] = (
        with_alpha(contrast(footer_fill), 0.5) if footer_fill == copyright_fill else footer_contrast
    )
    values['o-footer-scrolltop-hover-bg'] = copyright_fill
    values['o-footer-scrolltop-hover-color'] = contrast(copyright_fill, main_background=footer_fill)
    # The portal cards' hover.
    portal_card = area_color('portal-card') or body_background
    values['o-portal-card-hover-bg'] = (
        tint_color(portal_card, 15) if lightness(portal_card) < 35 else shade_color(portal_card, 15)
    )
    menu = area_color('menu')
    gates = {
        'menu-dark': bool(menu) and contrast(menu) != contrast.dark,
        'body-dark': lightness(body_background) < 50,
    }
    return values, gates


THEME_COLORS = ('primary', 'secondary', 'success', 'info', 'warning', 'danger', 'light', 'dark')


def _compute_root(colors, contrast, user_keys):
    """The `:root` values of Bootstrap that website computes from the colors
    (see `o-after-bootstrap-root`)."""
    values = {}
    body_background = colors['o-cc1-bg']
    body_color = colors.get('o-cc1-text') or contrast(body_background)
    for name in THEME_COLORS:
        if name in colors:
            values[f'{name}-rgb'] = colors[name]
    primary = colors['primary']
    is_dark_palette = contrast(body_color) == contrast.dark
    if is_dark_palette:
        values['primary-text-emphasis'] = tint_color(primary, 40)
    elif not has_enough_contrast(primary, body_background):
        values['primary-text-emphasis'] = increase_contrast(primary, body_background)
    else:
        values['primary-text-emphasis'] = shade_color(primary, 60)
    values['primary-bg-subtle'] = shade_color(primary, 70) if is_dark_palette else tint_color(primary, 80)
    values['body-bg-rgb'] = body_background
    for name in ('body-color-rgb', 'secondary-color-rgb', 'tertiary-color-rgb'):
        values[name] = body_color
    if '200' in colors:
        values['secondary-bg-rgb'] = colors['200']
    values['tertiary-bg-rgb'] = mix(contrast(body_background), body_background, 10)
    link = colors.get('o-cc1-link') or primary
    if 'o-cc1-link' not in user_keys:
        link = increase_contrast(link, body_background)
    link_hover = adjust_lightness(link, -15)
    if 'o-cc1-link' not in user_keys:
        link_hover = increase_contrast(link_hover, body_background)
    values['link-color-rgb'] = link
    values['link-hover-color'] = link_hover
    values['link-hover-color-rgb'] = link_hover
    values['o-btn-link-focus-shadow-rgb'] = mix(contrast(link), link, 15)
    for name in THEME_COLORS:
        if color := colors.get(name):
            # Bootstrap's `.link-<color>` hover.
            is_light = contrast(color) == contrast.light
            values[f'{name}-link-hover-rgb'] = shade_color(color, 20) if is_light else tint_color(color, 20)
            # The badges' (website.scss).
            values[f'{name}-badge-text'] = increase_contrast(color, tint_color(color, 90))
            values[f'{name}-badge-contrast'] = contrast(color, min_ratio=3)
    if dark := colors.get('dark'):
        values.update(_variant_colors('o-figure-caption', with_alpha(dark, 0.6), contrast))
    # The inputs, cards' body and dropdowns (see website's
    # `o-after-bootstrap-root`).
    values['o-input-color'] = contrast(colors.get('input') or body_background)
    if body := colors.get('body'):
        values['o-body-fill'] = opaque(WHITE, body)
    values.update(_variant_colors('o-card-body-bg', with_alpha(body_background, 0.9), contrast))
    values['o-dropdown-link-active-color'] = contrast(with_alpha(contrast(body_background), 0.2))

    # The utilities' variants (see web's `o-print-variant-colors`).
    variant_names = [*THEME_COLORS, *GRAYS, *(f'o-color-{i}' for i in range(1, 6))]
    for name in variant_names:
        if color := colors.get(name):
            values.update(_variant_colors(name, color, contrast))
    # The buttons (see website's `o-after-bootstrap-root`): primary and
    # secondary are the first color combination's.
    for name in THEME_COLORS:
        if name not in colors:
            continue
        if name in ('primary', 'secondary'):
            button = colors.get(f'o-cc1-btn-{name}') or colors[name]
            border = colors.get(f'o-cc1-btn-{name}-border') or button
        else:
            button = border = colors[name]
            variant = contrast.button_variant(button, border)
            values[f'o-btn-fill-{name}-text'] = variant.pop('color')
            variant.pop('disabled-color')
            values.update({f'o-btn-fill-{name}-{key}': value for key, value in variant.items()})
        outline = increase_contrast(border, body_background)
        values[f'o-btn-outline-{name}'] = outline
        values[f'o-btn-outline-{name}-contrast'] = contrast(outline)
        values[f'o-btn-outline-{name}-rgb'] = outline
    return values


GRAYS = ('100', '200', '300', '400', '500', '600', '700', '800', '900', 'white', 'black')


def _variant_colors(name, color, contrast):
    """web's `o-print-variant-colors()`: the text and background utilities'
    colors (frontend's `text-emphasis-variant()` and `bg-variant()`)."""
    values = {}
    if color[3] > 0.3:
        values[f'{name}-contrast'] = contrast(color)
    values[f'{name}-text-hover'] = adjust_lightness(color, -20)
    hover = adjust_lightness(color, -10)
    values[f'{name}-bg-hover'] = hover
    if hover[3] > 0.3:
        values[f'{name}-bg-hover-contrast'] = contrast(hover)
    return values


def _compute_combination(cc, colors, contrast, user_keys):
    """html_editor's `:root` prints of a color combination."""
    values = {}
    background = colors[f'{cc}-bg']
    values[f'{cc}-bg-contrast'] = contrast(background)

    def auto_contrast(color):
        if f'{cc}-link' in user_keys:
            return color
        return increase_contrast(color, background)

    link = colors.get(f'{cc}-link') or colors['primary']
    values[f'{cc}-link'] = auto_contrast(link)
    values[f'{cc}-link-hover'] = auto_contrast(adjust_lightness(link, -15))
    for button_type in ('primary', 'secondary'):
        name = f'{cc}-btn-{button_type}'
        button = colors.get(name)
        button_color = button or colors[button_type]
        border = colors.get(f'{name}-border') or button_color
        variant = contrast.button_variant(button_color, border)
        values[f'{name}-text'] = variant.pop('color')
        variant.pop('disabled-color')
        values.update({f'{name}-{key}': value for key, value in variant.items()})
        outline = button_color if button else increase_contrast(border, background)
        values[f'{name}-outline'] = outline
        outline_variant = contrast.button_outline_variant(outline)
        values[f'{name}-outline-contrast'] = outline_variant['hover-color']
        values[f'{name}-outline-rgb'] = outline
    values[f'{cc}-btn-close-filter'] = 'initial' if lightness(background) < 50 else 'none'
    return values
