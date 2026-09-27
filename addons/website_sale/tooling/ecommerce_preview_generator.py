"""Regenerate the eCommerce configurator previews: one self-contained, JS-free
page per shop and product page style, written where ``const.py`` points its
``preview_url``. Sibling of ``design-themes/tooling/theme_preview_generator``.

Run: ``python addons/website_sale/tooling/ecommerce_preview_generator.py``
"""

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup


WEBSITE_SALE_DIR = Path(__file__).resolve().parents[1]
ADDONS_DIR = WEBSITE_SALE_DIR.parent
ODOO_DIR = ADDONS_DIR.parent
ODOO_BIN = ODOO_DIR / "odoo-bin"
LOGIN = "admin"
PASSWORD = "admin"

BASE_DATABASE = "generate-ecommerce-html"
BASE_HTTP_PORT = 8889
NUM_WORKERS = int(os.environ.get("PREVIEW_WORKERS", min(4, os.cpu_count() or 1)))
BOOT_STAGGER_SECONDS = 3
STYLESHEET_FETCH_WORKERS = 6

GENERIC_ODOO_ARGS = [
    f"--addons-path={ADDONS_DIR}",
    "--log-handler=:WARNING",
    "--max-cron-threads=0",
]


def build_odoo_args(database, port, *extra_args):
    return [
        "--http-interface=localhost",
        f"--http-port={port}",
        f"--database={database}",
        *GENERIC_ODOO_ARGS,
        *extra_args,
    ]


# The palette must stay the one ``PALETTE_COLORS`` tokenizes.
CONFIGURATOR_VALUES = {
    "industry_id": 0,
    "industry_name": "business",
    "selected_features": [],
    "selected_palette": "base-1",
    "website_purpose": "general",
    "website_type": "ecommerce",
    "skip_ai": True,
    "theme_name": "theme_default",
}

DOWNLOAD_SESSION = requests.Session()
DOWNLOAD_SESSION.headers["User-Agent"] = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

PSEUDO_RE = re.compile(r'::?[a-zA-Z-]+(\([^)]*\))?')


CSS_URL_RE = re.compile(
    r'url\(\s*'
    r'(?:"([^"]*)"|\'([^\']*)\'|([^)]*))'
    r'\s*\)'
)


VH_RE = re.compile(r"(-?(?:\d+(?:\.\d+)?|\.\d+))s?vh")


COLOR_TOKEN_END = r"(?![0-9a-zA-Z_-])"


PALETTE_COLORS = {
    "--o-color-1": ("#714B67",),
    "--o-color-2": ("#F0CDA8",),
    "--o-color-3": ("#F6F5F4",),
    "--o-color-4": ("#FFFFFF", "#FFF"),
    "--o-color-5": ("#1B1319",),
}


def hex_to_rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))


# The text color ``color-contrast()`` froze against the generation palette.
CONTRAST_TEXT_VAR = "--o-cc1-text"
CONTRAST_TEXT_COLOR = "#212529"

# The same colors as bare RGB components, out of reach of the hex tokenization.
PALETTE_RGB_COLORS = {
    hex_to_rgb(colors[0]): css_var for css_var, colors in PALETTE_COLORS.items()
} | {hex_to_rgb(CONTRAST_TEXT_COLOR): CONTRAST_TEXT_VAR}

# How far a mix may go before it stops being recognizable as its palette color.
MIX_RATIO_RANGE = (0.05, 0.98)

COMPONENT = r"\d{1,3}(?:\.\d+)?"
# ``--link-color-rgb: 100.73829787, 66.86170213, 91.82340426``.
RGB_VARIABLE_RE = re.compile(
    rf"(--[\w-]+-rgb)\s*:\s*({COMPONENT})\s*,\s*({COMPONENT})\s*,\s*({COMPONENT})\s*[;}}]"
)
# ``rgba(var(--light-rgb), var(--bg-opacity, 1))``: one nested var() at most.
RGB_VARIABLE_USE_RE = re.compile(
    r"rgba?\(\s*var\((--[\w-]+-rgb)\)\s*(?:,\s*((?:[^()]|var\([^()]*\))*?)\s*)?\)",
    re.I,
)
RGBA_RE = re.compile(
    rf"rgba?\(\s*({COMPONENT})\s*,\s*({COMPONENT})\s*,\s*({COMPONENT})\s*(?:,\s*([\d.]+)\s*)?\)",
    re.I,
)
HEX_COLOR_RE = re.compile(rf"#([0-9a-fA-F]{{6}}|[0-9a-fA-F]{{3}}){COLOR_TOKEN_END}")


FONT_MIME_TYPES = {
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".eot": "application/vnd.ms-fontobject",
}


FONT_ASSET_URLS = {
    "web.material_symbols_outlined.min.woff2": "/web/static/src/libs/materialsymbols/material_symbols_outlined_subset.woff2",
    "web.material_symbols_sharp.min.woff2": "/web/static/src/libs/materialsymbols/material_symbols_sharp_subset.woff2",
    "web.odoo_ui_icons.min.woff2": "/web/static/lib/odoo_ui_icons/fonts/odoo_ui_icons.woff2",
}


DEFAULT_WEBSITE_LOGO_URL = "/website/static/src/img/website_logo.svg"


WEBSITE_LOGO_URL_RE = re.compile(r"/web/image/website/\d+/logo(?:[/?#].*)?")


VH_TO_VW_RATIO = 10 / 16


# Previews are shown at about a third of their width, where a hairline border
# falls under one device pixel and vanishes. Zero stays zero: it means no border.
MIN_BORDER_WIDTH = 3
BORDER_DECLARATION_RE = re.compile(r"([\w-]*border[\w-]*\s*:\s*)([^;{}]*)", re.I)
BORDER_LENGTH_RE = re.compile(r"(\d*\.?\d+)px")


TEXT_KEY_ATTRIBUTE = "industry_text_key"
IMAGE_KEY_ATTRIBUTE = "industry_image_key"
LOGO_ATTRIBUTE = "preview_logo"
# Attributes the page repeats a product or category name in.
LEAKED_TEXT_ATTRIBUTES = ("alt", "title", "aria-label", "data-name")
# Record images only resolve in the database that generated the page.
RECORD_IMAGE_RE = re.compile(r"^/web/image/(\w+\.\w+/\d+)/")
# The header logo, already rewritten to a static URL by ``inline_images``.
LOGO_SELECTOR = "header img, #top img, .navbar-brand img"

CATEGORIES_IMG_DIR = "/website_sale/static/src/img/categories"
PRODUCTS_IMG_DIR = "/website_sale/static/src/img/products_demo"

# The fake catalog. Only the shop's first page is previewed, so the counts are
# what a visitor sees: no pager, no second row of categories.
CATEGORY_DATA = [
    # name, static image
    ("Desks", "desks.jpg"),
    ("Cabinets", "cabinets.jpg"),
    ("Drawers", "drawers.jpg"),
    ("Lamps", "lamps.jpg"),
    ("Storage", "boxes.jpg"),
    ("Seating", "furnitures.jpg"),
    ("Bins", "bins.jpg"),
    ("Desk Parts", "desk_components.jpg"),
]
PRODUCT_DATA = [
    # name, price, description, static image
    ("Corner Desk", 420.00, "Solid oak top on a powder-coated steel frame.",
     "product_product_5-image_02.jpg"),
    ("Desk Lamp", 39.00, "Articulated arm with a warm dimmable light.",
     "product_lamp_02.jpg"),
    ("Office Chair", 189.00, "Adjustable headrest and breathable backrest.",
     "product_product_16-image_02.jpg"),
    ("Storage Cabinet", 245.00, "Two doors, three shelves, soft-close hinges.",
     "product_product_12-image_02.jpg"),
    ("Filing Pedestal", 159.00, "Three drawers on casters, fits under any desk.",
     "product_product_27-image_02.jpg"),
    ("Writing Desk", 340.00, "Compact desk with two hidden drawers.",
     "table02_02.jpg"),
    ("Work Pod", 890.00, "Acoustic shell for focused work in open spaces.",
     "product_product_24-image_02.jpg"),
    ("Drawer Unit", 199.00, "Oak front on a matte black steel body.",
     "product_product_10-image_02.jpg"),
    ("Desk Organizer", 12.50, "Perforated steel holder for pens and tools.",
     "desk_organizer_02.jpg"),
    ("Floor Mat", 65.00, "Protects hard floors from chair casters.",
     "floor_protection-image_02.jpg"),
]

# The industry pictures, by the shape the slot showing them is cropped to.
SQUARE_IMAGE_KEYS = [f"website.cat_stud_sq_{index}" for index in range(1, 9)]
PORTRAIT_IMAGE_KEYS = [f"website.prod_sq_{index}" for index in range(1, 11)]
LANDSCAPE_IMAGE_KEYS = [
    "website.prod_ls_1",
    "website.prod_ls_1_bis",
    "website.prod_ls_1_ter",
]

# The pictures a shop style gives its categories and products, cycled if short.
SHOP_IMAGE_KEYS = {
    # option: category pictures, product pictures
    "classic_grid": (SQUARE_IMAGE_KEYS, SQUARE_IMAGE_KEYS),
    "chips_contained": (SQUARE_IMAGE_KEYS, SQUARE_IMAGE_KEYS),
    "condensed_list": (SQUARE_IMAGE_KEYS, SQUARE_IMAGE_KEYS),
    "modern_grid": (SQUARE_IMAGE_KEYS, PORTRAIT_IMAGE_KEYS),
    # A showcase row is a wide band, and the same picture fills all of them.
    "showcase": (SQUARE_IMAGE_KEYS, LANDSCAPE_IMAGE_KEYS[:1]),
    "cards": (SQUARE_IMAGE_KEYS, SQUARE_IMAGE_KEYS),
}

# The angles the previewed product shows, written per style on its own copy.
PRODUCT_PAGE_SQUARE_IMAGES = [
    # static image, industry image
    ("product_product_5-image_02.jpg", "website.prod_sq_1"),
    ("product_product_3-image_02.jpg", "website.prod_sq_1_bis"),
    ("product_product_6-image_02.jpg", "website.prod_sq_1_ter"),
    ("product_product_7-image_02.jpg", "website.prod_sq_1_quater"),
]
PRODUCT_PAGE_LANDSCAPE_IMAGES = [
    ("product_product_5-image_02.jpg", "website.prod_ls_1"),
    ("product_product_9-image_02.jpg", "website.prod_ls_1_bis"),
    ("product_product_d01_image_02.jpg", "website.prod_ls_1_ter"),
]
# `large_grid` and `large_image` crop to 16/9 and 21/9, `focused` shows one.
PRODUCT_PAGE_IMAGES = {
    "classic": PRODUCT_PAGE_SQUARE_IMAGES,
    "image_grid": PRODUCT_PAGE_SQUARE_IMAGES,
    "functional": PRODUCT_PAGE_SQUARE_IMAGES,
    "focused": PRODUCT_PAGE_SQUARE_IMAGES[:1],
    "large_grid": PRODUCT_PAGE_LANDSCAPE_IMAGES,
    "large_image": PRODUCT_PAGE_LANDSCAPE_IMAGES,
}


CATEGORIES = [
    {
        "name": name,
        "image": f"{CATEGORIES_IMG_DIR}/{filename}",
    }
    for name, filename in CATEGORY_DATA
]
PRODUCTS = [
    {
        "name": name,
        "price": price,
        "description": description,
        "image": f"{PRODUCTS_IMG_DIR}/{filename}",
    }
    for name, price, description, filename in PRODUCT_DATA
]


def get_shop_image_keys(option):
    """Give every category and product of the catalog its picture, for a style."""
    category_keys, product_keys = SHOP_IMAGE_KEYS[option]
    return {
        item["name"]: keys[index % len(keys)]
        for keys, items in ((category_keys, CATEGORIES), (product_keys, PRODUCTS))
        for index, item in enumerate(items)
    }


def get_product_page_images(option):
    return [
        {"image": f"{PRODUCTS_IMG_DIR}/{filename}", "image_key": image_key}
        for filename, image_key in PRODUCT_PAGE_IMAGES[option]
    ]


def get_product_page_texts(images):
    """Map the product page's fixed texts to the key of the picture beside them."""
    return {
        CATEGORIES[0]["name"]: f"{SQUARE_IMAGE_KEYS[0]}.category_name",
        PRODUCTS[0]["name"]: f'{images[0]["image_key"]}.product_name',
        f'{PRODUCTS[0]["price"]:.2f}': f'{images[0]["image_key"]}.price',
    }


def get_preview_texts(image_keys):
    """Map each rendered catalog text to the key of the picture beside it."""
    preview_texts = {}

    def add(text, key):
        # A text mapped twice would hand one slot another slot's row.
        existing = preview_texts.get(text)
        if existing is not None and existing != key:
            raise RuntimeError(f"{text!r} would stamp both {existing} and {key}.")
        preview_texts[text] = key

    for category in CATEGORIES:
        add(category["name"], f'{image_keys[category["name"]]}.category_name')
    for product in PRODUCTS:
        add(product["name"], f'{image_keys[product["name"]]}.product_name')
        add(f'{product["price"]:.2f}', f'{image_keys[product["name"]]}.price')
    return preview_texts


def stop_odoo(server):
    if server.poll() is not None:
        return
    server.terminate()
    try:
        server.wait(timeout=30)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait()


def jsonrpc(session, url, params, timeout=30):
    response = session.post(
        url,
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": 1,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(json.dumps(payload["error"], indent=2))
    return payload["result"]


def root_relative_url(url, base_url):
    if not url or url.startswith(("data:", "#")):
        return url
    parsed = urlsplit(urljoin(base_url, url))
    path = parsed.path or "/"
    if parsed.query:
        path += f"?{parsed.query}"
    if parsed.fragment:
        path += f"#{parsed.fragment}"
    return path


def is_external_url(url, base_url):
    parsed = urlsplit(urljoin(base_url, url))
    base = urlsplit(base_url)
    return bool(parsed.netloc and parsed.netloc != base.netloc)


def get_font_mime_type(url):
    suffix = Path(urlsplit(url).path).suffix.lower()
    return FONT_MIME_TYPES.get(suffix)


def resolve_css_imports(css, base_url):
    def replace(match):
        url = match.group(1) or match.group(2)
        if not url:
            return ""
        raw, _ = fetch(urljoin(base_url, url))
        if not raw:
            return ""
        return resolve_css_imports(raw.decode("utf-8", errors="replace"), urljoin(base_url, url))

    return re.sub(
        r'@import\s+(?:url\(["\']?([^)"\']+)["\']?\)|["\']([^"\']+)["\'])\s*;',
        replace,
        css,
    )


def resolve_css_urls(css, base_url, quote='"'):
    def replace(match):
        raw_url, _quote = get_css_url(match)
        if raw_url.startswith("data:"):
            return match.group(0)
        font_asset_url = get_stable_font_asset_url(raw_url)
        if font_asset_url:
            return f'url({quote}{font_asset_url}{quote})'
        if get_font_mime_type(raw_url):
            if is_external_url(raw_url, base_url):
                return f'url({quote}{urljoin(base_url, raw_url)}{quote})'
            return f'url({quote}{root_relative_url(raw_url, base_url)}{quote})'
        return f'url({quote}{root_relative_url(raw_url, base_url)}{quote})'

    return CSS_URL_RE.sub(replace, css)


def get_stable_font_asset_url(url):
    filename = Path(urlsplit(url).path).name
    return FONT_ASSET_URLS.get(filename)


def get_css_url(match):
    double_quoted_url, single_quoted_url, unquoted_url = match.groups()
    if double_quoted_url is not None:
        return double_quoted_url, '"'
    if single_quoted_url is not None:
        return single_quoted_url, "'"
    return unquoted_url.strip(), ""


def replace_color_token(text, color, replacement):
    # Do not replace #FFF inside #FFF3CD or %23FFF inside %23FFF3CD.
    return re.sub(
        rf"{re.escape(color)}{COLOR_TOKEN_END}",
        replacement,
        text,
        flags=re.I,
    )


def replace_palette_colors_in_css(css_text):
    protected = {}
    for css_var, colors in PALETTE_COLORS.items():
        for color in colors:
            placeholder = f"__KEEP_{css_var.strip('-').replace('-', '_')}_{len(protected)}__"
            pattern = re.compile(
                rf"({re.escape(css_var)}\s*:\s*)"
                rf"{re.escape(color)}{COLOR_TOKEN_END}",
                re.I,
            )
            css_text = pattern.sub(lambda match: f"{match.group(1)}{placeholder}", css_text)
            protected[placeholder] = color

    for css_var, colors in PALETTE_COLORS.items():
        for color in colors:
            css_text = replace_color_token(css_text, color, f"var({css_var})")

    for placeholder, color in protected.items():
        css_text = css_text.replace(placeholder, color)
    return css_text


def palette_color(rgb):
    css_var = PALETTE_RGB_COLORS.get(tuple(round(component) for component in rgb))
    return f"var({css_var})" if css_var else None


def palette_color_mix(rgb):
    """Rebuild a color Bootstrap froze by mixing a palette color with black or white."""
    minimum, maximum = MIX_RATIO_RANGE
    for palette_rgb, css_var in PALETTE_RGB_COLORS.items():
        for mixed, components, palette_components in (
            ("black", rgb, palette_rgb),
            ("white", [255 - c for c in rgb], [255 - c for c in palette_rgb]),
        ):
            if not all(palette_components):
                continue
            ratio = sum(c / p for c, p in zip(components, palette_components)) / 3
            if not minimum <= ratio <= maximum:
                continue
            if any(abs(c - p * ratio) > 1 for c, p in zip(components, palette_components)):
                continue
            return f"color-mix(in srgb, {mixed} {(1 - ratio) * 100:.4g}%, var({css_var}))"
    return None


def palette_color_expression(color, alpha):
    if alpha is None:
        return color
    # A CSS variable cannot hold RGB components, so the opacity moves to a mix.
    if re.fullmatch(r"[\d.]+", alpha):
        alpha = f"{float(alpha) * 100:g}%"
    else:
        alpha = f"calc({alpha} * 100%)"
    return f"color-mix(in srgb, {color} {alpha}, transparent)"


def replace_derived_palette_colors_in_css(css_text):
    """Re-link what the hex pass cannot see: bare RGB components, frozen contrast text."""
    rgb_variables = {}
    for name, *components in RGB_VARIABLE_RE.findall(css_text):
        rgb = [float(component) for component in components]
        if color := palette_color(rgb) or palette_color_mix(rgb):
            rgb_variables[name] = color

    def replace_variable_use(match):
        color = rgb_variables.get(match.group(1))
        return palette_color_expression(color, match.group(2)) if color else match.group(0)

    def replace_literal(match):
        rgb = [float(component) for component in match.group(1, 2, 3)]
        color = palette_color(rgb) or palette_color_mix(rgb)
        return palette_color_expression(color, match.group(4)) if color else match.group(0)

    def replace_hex(match):
        color = match.group(1)
        if len(color) == 3:
            color = "".join(component * 2 for component in color)
        rgb = hex_to_rgb(color)
        # What is left of an exact palette color is its own declaration.
        if palette_color(rgb):
            return match.group(0)
        return palette_color_mix(rgb) or match.group(0)

    css_text = RGB_VARIABLE_USE_RE.sub(replace_variable_use, css_text)
    css_text = RGBA_RE.sub(replace_literal, css_text)
    css_text = HEX_COLOR_RE.sub(replace_hex, css_text)
    # Everything but its own declaration, which stays the offline fallback.
    declaration = f"{CONTRAST_TEXT_VAR}: {CONTRAST_TEXT_COLOR}"
    css_text = replace_color_token(
        css_text.replace(declaration, "__KEEP_CONTRAST_TEXT__"),
        CONTRAST_TEXT_COLOR,
        f"var({CONTRAST_TEXT_VAR})",
    )
    return css_text.replace("__KEEP_CONTRAST_TEXT__", declaration)


def replace_palette_colors_in_url(url):
    for css_var, colors in PALETTE_COLORS.items():
        color_token = css_var.removeprefix("--")
        for color in colors:
            encoded_color = "%23" + color.lstrip("#")
            url = replace_color_token(url, encoded_color, color_token)
    return url


def replace_palette_colors_in_urls(text):
    def replace(match):
        raw_url, quote = get_css_url(match)
        if raw_url.startswith("data:"):
            # Inline SVG icons need real colors, not palette tokens.
            return match.group(0)
        url = replace_palette_colors_in_url(raw_url)
        return f"url({quote}{url}{quote})"

    return CSS_URL_RE.sub(replace, text)


def replace_palette_colors_in_style(style_text):
    style_text = replace_palette_colors_in_urls(style_text)
    for css_var, colors in PALETTE_COLORS.items():
        for color in colors:
            style_text = replace_color_token(style_text, color, f"var({css_var})")
    return style_text


def replace_palette_colors_in_attributes(soup):
    for tag in soup.find_all(True):
        for attribute in ("fill", "stroke", "stop-color", "color"):
            value = tag.get(attribute)
            if not value:
                continue
            tag[attribute] = replace_palette_colors_in_style(value)


def inject_palette_variables(soup):
    if soup.head is None:
        soup.html.insert(0, soup.new_tag("head"))
    style = soup.new_tag("style")
    style["id"] = "preview-palette-vars"
    style.string = ":root{" + " ".join(
        f"{css_var}: {colors[0]};" for css_var, colors in PALETTE_COLORS.items()
    ) + "}"
    soup.head.append(style)


def inject_color_combination_text_overrides(soup):
    if soup.head is None:
        soup.html.insert(0, soup.new_tag("head"))

    heading_selectors = "h1, h2, h3, h4, h5, h6, .h1, .h2, .h3, .h4, .h5, .h6"
    rules = []
    for index in range(1, 6):
        text_color = f"var(--o-cc{index}-text)"
        rules.append(f".o_cc{index}{{--color:{text_color};color:{text_color};}}")
        rules.append(
            f".o_cc{index} :is({heading_selectors}),"
            f".o_colored_level .o_cc{index} :is({heading_selectors})"
            f"{{color:{text_color};}}"
        )

    style = soup.new_tag("style")
    style["id"] = "preview-color-combination-text-overrides"
    style.string = "".join(rules)
    soup.head.append(style)


def inject_image_overlay_text_overrides(soup):
    """Keep a label printed over an image white, whatever the palette does to ``$white``."""
    if soup.head is None:
        soup.html.insert(0, soup.new_tag("head"))

    style = soup.new_tag("style")
    style["id"] = "preview-image-overlay-text-overrides"
    # Two classes, like the rule it overrides, so being last is enough to win.
    style.string = (
        ".o_wsale_filmstrip_container.o_wsale_filmstrip_large_images{"
        "--o-wsale-filmstrip-item-color: #FFF;"
        "--o-wsale-filmstrip-item-color-active: #FFF;"
        "}"
    )
    soup.head.append(style)


def convert_vh_to_vw(css_text, ratio=VH_TO_VW_RATIO):
    if "vh" not in css_text:
        return css_text

    def replace(match):
        vw = float(match.group(1)) * ratio
        return f"{vw:g}vw"

    return VH_RE.sub(replace, css_text)


def enforce_minimum_border_width(css_text):
    def widen(match):
        width = float(match.group(1))
        return f"{MIN_BORDER_WIDTH}px" if 0 < width < MIN_BORDER_WIDTH else match.group(0)

    def replace(match):
        property_name, value = match.groups()
        if re.search(r"radius|spacing|collapse|image", property_name, re.I):
            return match.group(0)
        return property_name + BORDER_LENGTH_RE.sub(widen, value)

    return BORDER_DECLARATION_RE.sub(replace, css_text)


def remove_parallax_fixed_background(css_text):
    def replace(match):
        selector = match.group(1)
        body = match.group(2)
        if ".s_parallax_bg" not in selector:
            return match.group(0)
        body = re.sub(r"\s*background-attachment\s*:\s*fixed\s*;?", "", body, flags=re.I)
        return f"{selector}{{{body}}}"

    return re.sub(r"([^{}]+)\{([^{}]*)\}", replace, css_text)


def process_css(css_text, base_url):
    css_text = resolve_css_imports(css_text, base_url)
    css_text = resolve_css_urls(css_text, base_url)
    css_text = convert_vh_to_vw(css_text)
    css_text = enforce_minimum_border_width(css_text)
    css_text = remove_parallax_fixed_background(css_text)
    css_text = replace_palette_colors_in_urls(css_text)
    css_text = replace_palette_colors_in_css(css_text)
    return replace_derived_palette_colors_in_css(css_text)


def inline_stylesheets(soup, base_url):
    links = soup.find_all("link", rel=lambda rel: rel and "stylesheet" in rel)

    def fetch_link(link):
        href = link.get("href")
        if not href:
            return link, None, None
        abs_url = urljoin(base_url, href)
        raw, _ = fetch(abs_url)
        return link, abs_url, raw

    # Pure network I/O; the CPU-bound ``process_css`` stays sequential below.
    with ThreadPoolExecutor(max_workers=STYLESHEET_FETCH_WORKERS) as executor:
        fetched = list(executor.map(fetch_link, links))

    for link, abs_url, raw in fetched:
        if not raw:
            link.decompose()
            continue
        style = soup.new_tag("style")
        style.string = process_css(raw.decode("utf-8", errors="replace"), abs_url)
        link.replace_with(style)


def inline_style_blocks(soup, base_url):
    for style in soup.find_all("style"):
        if style.string:
            style.string = process_css(style.string, base_url)


def inline_inline_styles(soup, base_url):
    for tag in soup.find_all(style=True):
        # Single quotes: the url() ends up in a double-quoted style attribute.
        style = resolve_css_urls(tag["style"], base_url, quote="'")
        style = convert_vh_to_vw(style)
        tag["style"] = replace_palette_colors_in_style(style)


def inline_images(soup, base_url):
    for image in soup.find_all("img"):
        src = image.get("src", "")
        if src:
            src = root_relative_url(src, base_url)
            if WEBSITE_LOGO_URL_RE.fullmatch(src):
                src = DEFAULT_WEBSITE_LOGO_URL
            image["src"] = src
        image.attrs.pop("srcset", None)

    for source in soup.find_all("source"):
        source.attrs.pop("srcset", None)


def inline_font_preloads(soup, base_url):
    for link in soup.find_all("link", attrs={"as": "font"}):
        href = link.get("href")
        if not href:
            continue
        font_asset_url = get_stable_font_asset_url(href)
        if font_asset_url:
            link["href"] = font_asset_url
            continue
        if is_external_url(href, base_url):
            link["href"] = urljoin(base_url, href)
            continue
        link["href"] = root_relative_url(href, base_url)


def remove_preview_metadata(soup):
    for tag in soup.find_all("meta", property=lambda value: value in ("og:url", "og:image")):
        tag.decompose()
    for tag in soup.find_all("meta", attrs={"name": "twitter:image"}):
        tag.decompose()

    for link in soup.find_all("link"):
        rel = link.get("rel", [])
        rel = [rel] if isinstance(rel, str) else rel
        rel = {value.lower() for value in rel}
        if rel & {"canonical", "apple-touch-icon", "icon"}:
            link.decompose()


def remove_javascript(soup):
    for script in soup.find_all("script"):
        script.decompose()

    for noscript in soup.find_all("noscript"):
        noscript.unwrap()

    for tag in soup.find_all(True):
        for attribute in list(tag.attrs):
            if attribute.lower().startswith("on"):
                del tag[attribute]

    for link in soup.find_all("a", href=re.compile(r"^\s*javascript:", re.I)):
        link["href"] = "#"


def remove_javascript_dependent_classes(soup):
    # These keep an element invisible until frontend JS reveals it, and there is none.
    for removed_class in ("o_animate", "o_menu_loading"):
        for tag in soup.select(f".{removed_class}"):
            classes = [class_name for class_name in tag.get("class", []) if class_name != removed_class]
            if classes:
                tag["class"] = classes
            else:
                tag.attrs.pop("class", None)


def _skip_string(css, position):
    quote = css[position]
    position += 1
    while position < len(css):
        if css[position] == "\\":
            position += 2
            continue
        if css[position] == quote:
            return position + 1
        position += 1
    return position


def _skip_comment(css, position):
    end = css.find("*/", position + 2)
    return end + 2 if end != -1 else len(css)


def _find_block_end(css, start):
    depth = 1
    position = start + 1
    while position < len(css) and depth > 0:
        char = css[position]
        if char in ('"', "'"):
            position = _skip_string(css, position)
        elif char == "/" and position + 1 < len(css) and css[position + 1] == "*":
            position = _skip_comment(css, position)
        elif char == "{":
            depth += 1
            position += 1
        elif char == "}":
            depth -= 1
            position += 1
        else:
            position += 1
    return position


def _selector_is_used(soup, selector_text):
    for part in selector_text.split(","):
        cleaned = PSEUDO_RE.sub("", part).strip()
        if not cleaned:
            return True
        try:
            if soup.select_one(cleaned):
                return True
        except Exception:  # noqa: BLE001
            # An unparsable selector is kept: dropping its rule would break the page.
            return True
    return False


def _purge_css_text(css, soup):
    result = []
    position = 0
    while position < len(css):
        whitespace_start = position
        while position < len(css) and css[position] in " \t\n\r\f":
            position += 1
        if position >= len(css):
            result.append(css[whitespace_start:position])
            break

        if css[position:position + 2] == "/*":
            end = _skip_comment(css, position)
            result.append(css[whitespace_start:end])
            position = end
            continue

        if css[position] == "@":
            at_start = position
            position += 1
            while position < len(css) and (css[position].isalpha() or css[position] == "-"):
                position += 1
            keyword = css[at_start + 1:position].strip().lower()
            if keyword in ("import", "charset", "namespace"):
                end = css.find(";", position)
                if end == -1:
                    result.append(css[whitespace_start:])
                    break
                result.append(css[whitespace_start:end + 1])
                position = end + 1
            else:
                brace = css.find("{", position)
                if brace == -1:
                    result.append(css[whitespace_start:])
                    break
                end = _find_block_end(css, brace)
                result.append(css[whitespace_start:end])
                position = end
            continue

        brace = css.find("{", position)
        if brace == -1:
            result.append(css[whitespace_start:])
            break

        selector = css[position:brace].strip()
        end = _find_block_end(css, brace)
        rule_text = css[whitespace_start:end]
        if not selector or _selector_is_used(soup, selector):
            result.append(rule_text)
        position = end

    return "".join(result)


def purge_unused_css(soup):
    for style in soup.find_all("style"):
        if not style.string:
            continue
        cleaned = _purge_css_text(style.string, soup)
        if cleaned.strip():
            style.string = cleaned
        else:
            style.decompose()


def add_odoo_to_path():
    if str(ODOO_DIR) not in sys.path:
        sys.path.insert(0, str(ODOO_DIR))


def get_style_options():
    """Yield ``(configurator_apply keyword, option, preview_url path)`` per style."""
    # Imported on its own: ``odoo.addons.website_sale`` needs a configured addons path.
    add_odoo_to_path()
    if str(WEBSITE_SALE_DIR) not in sys.path:
        sys.path.append(str(WEBSITE_SALE_DIR))
    import const  # noqa: PLC0415

    for keyword, mapping in (
        ("shop_page_style_option", const.SHOP_PAGE_STYLE_MAPPING),
        ("product_page_style_option", const.PRODUCT_PAGE_STYLE_MAPPING),
    ):
        for option, config in mapping.items():
            yield keyword, option, ADDONS_DIR / Path(config["preview_url"]).relative_to("/")


def get_filestore_dir(database):
    """Where the attachments of a database live: a copy needs them too."""
    add_odoo_to_path()
    from odoo.tools import config  # noqa: PLC0415

    return Path(config.filestore(database))


def drop_database(database):
    # --force: a leftover connection would otherwise abort the whole run.
    subprocess.run(["dropdb", "--if-exists", "--force", database], check=True)
    shutil.rmtree(get_filestore_dir(database), ignore_errors=True)


def prepare_base_database():
    """Install ``website_sale`` and seed the catalog once; return the previewed product."""
    print(f"Preparing base database {BASE_DATABASE} (website_sale install, once).")  # noqa: T201
    drop_database(BASE_DATABASE)
    base_url = f"http://localhost:{BASE_HTTP_PORT}"
    # --without-demo: the demo catalog would show up next to the fake one.
    server = start_odoo(BASE_DATABASE, BASE_HTTP_PORT, "--init=website_sale", "--without-demo=True")
    session = requests.Session()
    try:
        wait_for_odoo(server, base_url)
        context = login(session, base_url, BASE_DATABASE).get("user_context", {})
        return seed_catalog(session, base_url, context)
    finally:
        session.close()
        stop_odoo(server)


def copy_database(target):
    """Clone the base database into ``target``, filestore included."""
    drop_database(target)
    subprocess.run(["createdb", "--template", BASE_DATABASE, target], check=True)
    filestore = get_filestore_dir(BASE_DATABASE)
    if filestore.is_dir():
        shutil.copytree(filestore, get_filestore_dir(target))


def start_odoo(database, port, *extra_args):
    command = [sys.executable, str(ODOO_BIN), *build_odoo_args(database, port, *extra_args)]
    return subprocess.Popen(command, cwd=ODOO_BIN.parent)


def wait_for_odoo(server, base_url):
    # Installing website_sale on an empty database takes a few minutes.
    deadline = time.time() + 900
    while time.time() < deadline:
        if server.poll() is not None:
            raise RuntimeError("Odoo stopped before it was ready.")
        try:
            response = requests.get(f"{base_url}/web/login", timeout=5)
            if response.ok:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise RuntimeError("Odoo did not start in time.")


def login(session, base_url, database):
    session_info = jsonrpc(
        session,
        f"{base_url}/web/session/authenticate",
        {"db": database, "login": LOGIN, "password": PASSWORD},
    )
    if not session_info.get("uid"):
        raise RuntimeError("Login failed.")
    return session_info


def call_kw(session, base_url, context, model, method, args, timeout=30):
    return jsonrpc(
        session,
        f"{base_url}/web/dataset/call_kw/{model}/{method}",
        {"model": model, "method": method, "args": args, "kwargs": {"context": context}},
        timeout=timeout,
    )


def fetch(url):
    try:
        response = DOWNLOAD_SESSION.get(url, timeout=30)
        response.raise_for_status()
        return response.content, response.headers.get("Content-Type", "")
    except requests.RequestException as error:
        print(f"  WARN: {url} - {error}", file=sys.stderr)  # noqa: T201
        return None, None


def encode_image(url):
    return base64.b64encode((ADDONS_DIR / url.lstrip("/")).read_bytes()).decode()


def seed_catalog(session, base_url, context):
    """Create the fake catalog and return the product whose page is previewed."""
    category_ids = call_kw(session, base_url, context, "product.public.category", "create", [[
        {
            "name": category["name"],
            "sequence": 10 * index,
            "image_1920": encode_image(category["image"]),
        }
        for index, category in enumerate(CATEGORIES)
    ]])
    product_ids = call_kw(session, base_url, context, "product.template", "create", [[
        {
            "name": product["name"],
            "list_price": product["price"],
            "description_sale": product["description"],
            "description_ecommerce": f"<p>{product['description']}</p>",
            "is_published": True,
            "website_sequence": 10 * index,
            # Every category needs a published product to show up in the shop.
            "public_categ_ids": [(6, 0, [category_ids[index % len(category_ids)]])],
            "image_1920": encode_image(product["image"]),
        }
        for index, product in enumerate(PRODUCTS)
    ]], timeout=300)
    return product_ids[0]


def set_product_page_images(session, base_url, context, product_id, images):
    """Give the previewed product the angles its page style shows."""
    call_kw(session, base_url, context, "product.template", "write", [[product_id], {
        "image_1920": encode_image(images[0]["image"]),
        # (5,) first: the copy comes with the single picture the tiles show.
        "product_template_image_ids": [(5,)] + [
            (0, 0, {"name": f"angle {index}", "image_1920": encode_image(image["image"])})
            for index, image in enumerate(images[1:], start=2)
        ],
    }], timeout=120)


def apply_configurator(session, base_url, context, style_keyword, option):
    return jsonrpc(
        session,
        f"{base_url}/web/dataset/call_kw/website/configurator_apply",
        {
            "model": "website",
            "method": "configurator_apply",
            "args": [],
            "kwargs": {**CONFIGURATOR_VALUES, style_keyword: option, "context": context},
        },
        timeout=900,
    )


def set_shop_page_size(session, base_url, context, website_id):
    # Show the whole fake catalog on the first page: the preview has no pager.
    call_kw(session, base_url, context, "website", "write", [[website_id], {"shop_ppg": len(PRODUCTS)}])


def stamp_texts(soup, preview_texts):
    """Mark every fake text so the configurator can substitute it."""
    for text_node in list(soup.find_all(string=True)):
        text = text_node.strip()
        key = preview_texts.get(text)
        if not key:
            continue
        parent = text_node.parent
        if not parent.find(True) and parent.get_text(strip=True) == text:
            parent.clear()
            parent.string = text
            parent[TEXT_KEY_ATTRIBUTE] = key
            continue
        # Mixed content: the text needs a span of its own, spacing left outside.
        span = soup.new_tag("span")
        span[TEXT_KEY_ATTRIBUTE] = key
        span.string = text
        leading = text_node[:len(text_node) - len(text_node.lstrip())]
        trailing = text_node[len(text_node.rstrip()):]
        text_node.replace_with(span)
        if leading:
            span.insert_before(leading)
        if trailing:
            span.insert_after(trailing)
    drop_leaked_texts(soup, preview_texts)


def drop_leaked_texts(soup, preview_texts):
    """Remove the fake texts the page repeats in its attributes, which no substitution reaches."""
    for tag in soup.find_all(True):
        for attribute in LEAKED_TEXT_ATTRIBUTES:
            value = tag.get(attribute)
            if isinstance(value, str) and value.strip() in preview_texts:
                del tag[attribute]


def stamp_record_images(soup, images):
    """Replace the product record images by static files, numbered by record not by tag."""
    records = []
    for tag in soup.find_all("img", src=RECORD_IMAGE_RE):
        record = RECORD_IMAGE_RE.match(tag["src"]).group(1)
        if record not in records:
            records.append(record)
        image = images[records.index(record)]
        tag["src"] = image["image"]
        tag[IMAGE_KEY_ATTRIBUTE] = image["image_key"]


def stamp_category_images(soup, image_keys):
    """Replace the inlined category images of the filmstrip by static files."""
    categories = {category["name"]: category for category in CATEGORIES}
    for item in soup.select(".o_wsale_filmstrip_item"):
        name = item.get_text(strip=True)
        category = categories.get(name)
        image = item.select_one(".o_wsale_filmstrip_image")
        if not category or not image:
            continue
        image["style"] = f"background-image:url('{category['image']}')"
        image[IMAGE_KEY_ATTRIBUTE] = image_keys[name]


def stamp_logo(soup):
    """Mark the header logo, which the configurator swaps in the loaded iframe."""
    logo = soup.select_one(LOGO_SELECTOR)
    if logo:
        logo[LOGO_ATTRIBUTE] = "1"


def stamp_shop_page(soup, image_keys, output_path):
    stamp_logo(soup)
    preview_texts = get_preview_texts(image_keys)
    stamp_texts(soup, preview_texts)
    stamp_category_images(soup, image_keys)
    products = {product["name"]: product for product in PRODUCTS}
    for tile in soup.select(".oe_product"):
        title = tile.select_one(".o_wsale_products_item_title")
        product = title and products.get(title.get_text(strip=True))
        if product:
            stamp_record_images(tile, [{
                "image": product["image"],
                "image_key": image_keys[product["name"]],
            }])
    warn_unstamped_texts(soup, preview_texts, output_path)


def stamp_product_page(soup, images, output_path):
    stamp_logo(soup)
    preview_texts = get_product_page_texts(images)
    stamp_texts(soup, preview_texts)
    stamp_record_images(soup, images)
    warn_unstamped_texts(soup, preview_texts, output_path)


def warn_unresolved_record_images(soup, output_path):
    leftovers = {
        value
        for tag in soup.find_all(True)
        for value in tag.attrs.values()
        if isinstance(value, str) and "/web/image/" in value
    }
    if leftovers:
        print(  # noqa: T201
            f"  WARN: {output_path.name} keeps database images: {sorted(leftovers)}",
            file=sys.stderr,
        )


def warn_unstamped_texts(soup, preview_texts, output_path):
    """Warn about a fake text left unmarked: it would survive every substitution."""
    leftovers = {
        text
        for text_node in soup.find_all(string=True)
        if (text := text_node.strip()) in preview_texts
        and TEXT_KEY_ATTRIBUTE not in text_node.parent.attrs
    }
    if leftovers:
        print(  # noqa: T201
            f"  WARN: {output_path.name} left unstamped: {sorted(leftovers)}",
            file=sys.stderr,
        )


def download_static_html(url, output_path, stamp):
    print(f"Downloading {url} -> {output_path}")  # noqa: T201
    raw, _ = fetch(url)
    if not raw:
        raise RuntimeError("Could not download the generated page.")

    soup = BeautifulSoup(raw, "html.parser")
    # Stamp first: the fake catalog is still rendered as the database wrote it.
    stamp(soup)
    inline_stylesheets(soup, url)
    inline_style_blocks(soup, url)
    inline_inline_styles(soup, url)
    inline_images(soup, url)
    inline_font_preloads(soup, url)
    remove_preview_metadata(soup)
    replace_palette_colors_in_attributes(soup)
    remove_javascript(soup)
    remove_javascript_dependent_classes(soup)
    purge_unused_css(soup)
    inject_palette_variables(soup)
    inject_color_combination_text_overrides(soup)
    inject_image_overlay_text_overrides(soup)
    warn_unresolved_record_images(soup, output_path)

    for meta in soup.find_all("meta", attrs={"http-equiv": True}):
        if meta["http-equiv"].lower() in ("refresh", "content-security-policy"):
            meta.decompose()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(str(soup), encoding="utf-8")


def generate_style_preview(database, port, style_keyword, option, output_path, product_id):
    print(f"Generating {option}")  # noqa: T201
    is_shop_page = style_keyword == "shop_page_style_option"
    base_url = f"http://localhost:{port}"

    copy_database(database)
    server = start_odoo(database, port)
    session = requests.Session()
    try:
        wait_for_odoo(server, base_url)
        context = login(session, base_url, database).get("user_context", {})
        result = apply_configurator(session, base_url, context, style_keyword, option)
        set_shop_page_size(session, base_url, context, result["website_id"])
        if is_shop_page:
            image_keys = get_shop_image_keys(option)
            path = "/shop"

            def stamp(soup):
                stamp_shop_page(soup, image_keys, output_path)
        else:
            page_images = get_product_page_images(option)
            set_product_page_images(session, base_url, context, product_id, page_images)
            path = f"/shop/{product_id}"

            def stamp(soup):
                stamp_product_page(soup, page_images, output_path)

        download_static_html(urljoin(base_url, path), output_path, stamp)
        print(f"Saved {output_path}")  # noqa: T201
    finally:
        session.close()
        stop_odoo(server)


def worker_database(worker_index):
    return f"{BASE_DATABASE}-{worker_index}"


def run_worker(worker_index, styles, product_id):
    """Generate a shard of the styles on this worker's own database and port."""
    port = BASE_HTTP_PORT + worker_index
    database = worker_database(worker_index)

    time.sleep(worker_index * BOOT_STAGGER_SECONDS)
    generated, failed = [], []
    for style_keyword, option, output_path in styles:
        try:
            generate_style_preview(database, port, style_keyword, option, output_path, product_id)
            generated.append(option)
        except Exception as error:  # noqa: BLE001
            # Whatever a style fails on, the shard keeps going and reports it.
            print(f"  ERROR {option}: {error}", file=sys.stderr)  # noqa: T201
            failed.append(option)
    drop_database(database)
    return generated, failed


def main():
    styles = list(get_style_options())
    num_workers = max(1, min(NUM_WORKERS, len(styles)))
    # Round-robin, so the heavier shop pages spread evenly over the workers.
    shards = [styles[index::num_workers] for index in range(num_workers)]

    print(f"Generating {len(styles)} previews across {num_workers} worker(s).")  # noqa: T201
    product_id = prepare_base_database()

    generated, failed = [], []
    if num_workers == 1:
        generated, failed = run_worker(0, shards[0], product_id)
    else:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(run_worker, index, shard, product_id): index
                for index, shard in enumerate(shards)
                if shard
            }
            for future in as_completed(futures):
                try:
                    worker_generated, worker_failed = future.result()
                    generated += worker_generated
                    failed += worker_failed
                except Exception as error:  # noqa: BLE001
                    # ``result()`` re-raises whatever killed the worker process.
                    print(f"Worker {futures[future]} crashed: {error}", file=sys.stderr)  # noqa: T201

    drop_database(BASE_DATABASE)
    print(f"Done. {len(generated)} generated, {len(failed)} failed.")  # noqa: T201
    if failed:
        print("Failed: " + ", ".join(sorted(failed)), file=sys.stderr)  # noqa: T201


if __name__ == "__main__":
    main()
