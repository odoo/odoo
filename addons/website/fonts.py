import re

import requests

GOOGLE_FONTS_CSS_URL = 'https://fonts.googleapis.com/'
# Google serves different font formats depending on the user agent. This header is used to get the latest version of the font.
GOOGLE_FONTS_CSS_HEADERS = {
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36',
}
GOOGLE_FONTS_CSS_TIMEOUT = 2

FONT_MIME_TYPES = {
    'woff2': 'font/woff2',
    'woff': 'font/woff',
    'truetype': 'font/ttf',
    'ttf': 'font/ttf',
    'opentype': 'font/otf',
    'otf': 'font/otf',
}

# Subset (as named in the comments of the Google Fonts stylesheets) in which the
# text of a language is written. Latin script languages (including the ones
# needing `latin-ext` or `vietnamese` for some characters) use `latin`, which
# always is needed. `None` means that no subset can be chosen (the CJK subsets
# are split in numbered chunks), nothing is preloaded.
FONT_SUBSET_BY_LANG = {
    **dict.fromkeys(['ru', 'uk', 'bg', 'sr', 'mk', 'be', 'kk', 'ky', 'mn', 'tg', 'tt', 'ce', 'ba', 'cv'], 'cyrillic'),
    'el': 'greek',
    'he': 'hebrew',
    **dict.fromkeys(['ar', 'fa', 'ur', 'ps', 'ku', 'ckb'], 'arabic'),
    **dict.fromkeys(['hi', 'mr', 'ne', 'sa'], 'devanagari'),
    'th': 'thai',
    'bn': 'bengali',
    'gu': 'gujarati',
    'pa': 'gurmukhi',
    'kn': 'kannada',
    'km': 'khmer',
    'ml': 'malayalam',
    'ta': 'tamil',
    'te': 'telugu',
    'si': 'sinhala',
    'ka': 'georgian',
    **dict.fromkeys(['ja', 'ko', 'zh'], None),
}

_FONT_FACE_RE = re.compile(r'(?:/\*\s*([^*]*?)\s*\*/\s*)?@font-face\s*\{([^}]*)\}')
_FONT_SRC_RE = re.compile(r'url\(\s*["\']?([^)"\']+?)["\']?\s*\)(?:\s*format\(\s*["\']?([\w-]+)["\']?\s*\))?')
_FONT_PRELOAD_EXPORT_RE = re.compile(r'--o-font-preload-\d+:\s*"([^"]*)"\s+(\d+)')


def get_font_subset(lang):
    """Return the font subset used to write the given language (e.g. `fr_FR`),
    `None` if it cannot be determined."""
    lang = (lang or 'en_US').lower()
    if lang.endswith('@latin'):
        return 'latin'
    return FONT_SUBSET_BY_LANG.get(re.split(r'[_@-]', lang)[0], 'latin')


def parse_font_preload_exports(scss_exports):
    """Extract from the CSS of the `website.font_urls_export` bundle the fonts
    to preload.

    :return: a list of `(stylesheet_url, weight)`, one per font role (body,
        headings)
    """
    return [
        (css_url, int(weight))
        for css_url, weight in _FONT_PRELOAD_EXPORT_RE.findall(scss_exports)
    ]


def read_font_stylesheet(env, css_url):
    """Return the content of a font stylesheet, either served by Google or
    stored in a public attachment, empty if it cannot be found.

    :raise requests.RequestException: if Google cannot be reached
    :raise UnicodeDecodeError: if the attachment is not a text file
    """
    if css_url.startswith(GOOGLE_FONTS_CSS_URL):
        response = requests.get(
            css_url, headers=GOOGLE_FONTS_CSS_HEADERS, timeout=GOOGLE_FONTS_CSS_TIMEOUT)
        response.raise_for_status()
        return response.text
    if match := re.match(r'/web/content/(\d+)/', css_url):
        attachment = env['ir.attachment'].sudo().browse(int(match[1])).exists()
        if attachment and attachment.public:
            return attachment.raw.decode()
    return ''


def parse_font_faces(css):
    """Extract the faces declared by a font stylesheet.

    :return: a tuple of `(subset, style, min_weight, max_weight, url, mime_type)`
        where `subset` is the name given by the comment preceding the
        `@font-face` (empty if none), and the weights are the same for
        static fonts and the bounds of the range for variable fonts. Faces
        without a supported font file are ignored.
    """
    faces = []
    for subset, body in _FONT_FACE_RE.findall(css):
        src = re.search(r'src:\s*([^;]+)', body)
        if not src:
            continue
        files = []
        for url, font_format in _FONT_SRC_RE.findall(src[1]):
            font_type = (font_format or url.partition('?')[0].rpartition('.')[2]).lower()
            if font_type in FONT_MIME_TYPES:
                files.append((font_type != 'woff2', url, FONT_MIME_TYPES[font_type]))
        if not files:
            continue
        # Prefer woff2, then keep the order of the stylesheet.
        _, url, mime_type = min(files, key=lambda f: f[0])
        style = re.search(r'font-style:\s*(\w+)', body)
        weight = re.search(r'font-weight:\s*(\d+)(?:\s+(\d+))?', body)
        min_weight = int(weight[1]) if weight else 400
        max_weight = int(weight[2] or weight[1]) if weight else 400
        faces.append((
            subset,
            style[1] if style else 'normal',
            min_weight,
            max_weight,
            url,
            mime_type,
        ))
    return tuple(faces)


def pick_font_face(faces, subset, weight):
    """Return the `(url, mime_type)` of the normal face of the given subset that
    the browser would use to render the given weight, `None` if there is none.

    Faces without subset are considered as matching any subset. When no face
    has the wanted weight, the closest one is chosen following the CSS font
    matching algorithm.
    """
    candidates = [
        # The weight rendered by a variable font is the wanted one clamped to its range.
        (max(min_weight, min(weight, max_weight)), url, mime_type)
        for face_subset, style, min_weight, max_weight, url, mime_type in faces
        if style == 'normal' and (not face_subset or face_subset == subset)
    ]
    if not candidates:
        return None

    def rank(candidate):
        face_weight = candidate[0]
        if face_weight == weight:
            return (0, 0)
        if 400 <= weight <= 500:
            # look for weights between the wanted one and 500, then below, then above
            if weight < face_weight <= 500:
                return (1, face_weight)
            if face_weight < weight:
                return (2, -face_weight)
            return (3, face_weight)
        if weight < 400:
            # look for weights below, then above
            return (1, -face_weight) if face_weight < weight else (2, face_weight)
        # look for weights above, then below
        return (1, face_weight) if face_weight > weight else (2, -face_weight)

    _, url, mime_type = min(candidates, key=rank)
    return url, mime_type
