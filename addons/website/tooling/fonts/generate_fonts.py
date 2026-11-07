#!/usr/bin/env python3

"""
Download Google fonts into the code, to be served as default local fonts.

For each font, the stylesheet Google serves is fetched along with every font file
it references, and stored in ``static/fonts/<Family_Name>/`` of the website
module:

* ``<Family_Name>.css`` -- the stylesheet, its ``url()`` rewritten to point at
  the files next to it.  The ``/* <subset> */`` comment preceding each
  ``@font-face`` is kept: it is what the server reads to preload the files of
  the subset matching the page language (see ``website._get_font_faces``).
* ``<family-name>-<subset>-<style>-<weight(s)>.woff2`` -- the font files.  Files
  shared by several faces (a variable font serves all its weights from a single
  file) are only stored once, the name giving the range of weights they cover.
* ``LICENSE.txt`` -- the license of the font, from the google/fonts repository.

A font is then declared in ``$o-theme-font-configs`` with a ``'local-url'``
instead of an ``'url'``; the script prints the declaration of each font it
downloaded.

The fonts are given as Google Fonts ``family`` specifications, the same as the
``'url'`` of ``$o-theme-font-configs`` (``Open+Sans:300,300i,400,400i``).  A bare
family name requests every weight, in both styles.  Without arguments, the
fonts declared with an ``'url'`` in ``$o-theme-font-configs`` of
``primary_variables.scss`` are downloaded.

With ``--module``, the fonts are stored in (and, without arguments, read from
the ``primary_variables.scss`` of) another module, e.g. a theme, so that it can
ship its own default fonts.

Usage
-----
::

    python3 generate_fonts.py                          # the default website fonts
    python3 generate_fonts.py Lato 'Open+Sans:400,700'
    python3 generate_fonts.py --subsets latin,latin-ext,cyrillic Roboto
    python3 generate_fonts.py --module ../design-themes/theme_bistro 'EB+Garamond:300,300i,400,400i,700,700i'
"""

import argparse
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

WEBSITE_PATH = Path(__file__).resolve().parents[2]  # .../website/tooling/fonts → .../website

# Same request as the stylesheet the website links to when a font is served by
# Google (see `font_urls_export.scss`), so that the local font has the same faces.
CSS_URL = "https://fonts.googleapis.com/css?family={family}&display=swap&subset=latin,latin-ext,vietnamese"
# Google serves the font format matching the user agent: this one gets woff2.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
# Where google/fonts keeps the fonts, by license.
LICENSE_URLS = (
    "https://raw.githubusercontent.com/google/fonts/main/ofl/{slug}/OFL.txt",
    "https://raw.githubusercontent.com/google/fonts/main/apache/{slug}/LICENSE.txt",
    "https://raw.githubusercontent.com/google/fonts/main/ufl/{slug}/UFL.txt",
)
# Same weights as the Google fonts added by the users (see
# `secondary_variables.scss`).
ALL_WEIGHTS = '100,100i,200,200i,300,300i,400,400i,500,500i,600,600i,700,700i,800,800i,900,900i'

FONT_FACE_RE = re.compile(r'(?:/\*\s*([^*]*?)\s*\*/\s*)?@font-face\s*\{([^}]*)\}')


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def primary_variables_path(module_path: Path) -> Path:
    return module_path / 'static' / 'src' / 'scss' / 'primary_variables.scss'


def default_families(module_path: Path) -> list[str]:
    """Return the `'url'` of the fonts of `$o-theme-font-configs`."""
    scss = primary_variables_path(module_path).read_text(encoding='utf-8')
    start = scss.index('$o-theme-font-configs: (')
    end = scss.index(') !default;', start)
    return re.findall(r"'url':\s*'([^']+)'", scss[start:end])


def parse_family(spec: str) -> tuple[str, str]:
    """Return the font name and the Google `family` parameter of *spec*."""
    name, _sep, weights = spec.partition(':')
    name = urllib.parse.unquote_plus(name).strip()
    return name, f"{name.replace(' ', '+')}:{weights or ALL_WEIGHTS}"


def slugify(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')


def write_if_changed(path: Path, content: bytes) -> bool:
    if path.is_file() and path.read_bytes() == content:
        return False
    path.write_bytes(content)
    return True


def download_font(spec: str, subsets: set[str] | None, module_path: Path = WEBSITE_PATH) -> str:
    """Download the font of *spec* into the static directory of the module at
    *module_path* and return its `$o-theme-font-configs` entry."""
    name, family = parse_family(spec)
    dir_name = name.replace(' ', '_')
    slug = slugify(name)
    font_dir = module_path / 'static' / 'fonts' / dir_name
    print(f"{name}")  # noqa: T201

    css = fetch(CSS_URL.format(family=family)).decode()
    faces = FONT_FACE_RE.findall(css)
    if not faces:
        raise SystemExit(f"  No @font-face in the stylesheet of {name!r}:\n{css[:600]}")

    # Name each file after the faces using it.
    faces_by_url = {}
    kept_faces = []
    for subset, body in faces:
        subset = subset or 'all'
        if subsets and subset not in subsets:
            continue
        url = re.search(r'url\(\s*["\']?([^)"\']+)', body)[1]
        style = re.search(r'font-style:\s*(\w+)', body)
        weight = re.search(r'font-weight:\s*(\d+)', body)
        faces_by_url.setdefault(url, []).append((
            slugify(subset) or 'all',
            style[1] if style else 'normal',
            int(weight[1]) if weight else 400,
        ))
        kept_faces.append((subset, body, url))

    file_names = {}
    for url, url_faces in faces_by_url.items():
        subset, style, _weight = url_faces[0]
        weights = sorted({weight for _subset, _style, weight in url_faces})
        weight_part = str(weights[0]) if len(weights) == 1 else f'{weights[0]}-{weights[-1]}'
        # Some files have no extension (`https://fonts.gstatic.com/l/font?kit=…`):
        # they are in the format requested with the user agent.
        _stem, dot, extension = urllib.parse.urlsplit(url).path.rpartition('/')[2].rpartition('.')
        extension = extension.lower() if dot else 'woff2'
        file_names[url] = f'{slug}-{subset}-{style}-{weight_part}.{extension}'
    if len(set(file_names.values())) != len(file_names):
        raise SystemExit(f"  Several files of {name!r} would get the same name.")

    font_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading {len(file_names)} files…")  # noqa: T201
    changed = 0
    for url, file_name in file_names.items():
        changed += write_if_changed(font_dir / file_name, fetch(url))

    css_blocks = [
        "/* Generated by `website/tooling/fonts/generate_fonts.py` -- do not edit manually. */\n",
    ]
    for subset, body, url in kept_faces:
        body = body.replace(url, f'./{file_names[url]}')
        css_blocks.append(f"/* {subset} */\n@font-face {{{body}}}\n")
    css_path = font_dir / f'{dir_name}.css'
    changed += write_if_changed(css_path, ''.join(css_blocks).encode())

    # The files of a previous version of the font.
    for path in font_dir.iterdir():
        if path.suffix in ('.woff2', '.woff', '.ttf') and path.name not in file_names.values():
            path.unlink()
            changed += 1

    for license_url in LICENSE_URLS:
        try:
            license_text = fetch(license_url.format(slug=slug.replace('-', '')))
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            continue
        changed += write_if_changed(font_dir / 'LICENSE.txt', license_text)
        break
    else:
        print(f"  ! No license found for {name!r}, add it to {font_dir} manually.")  # noqa: T201

    size = sum(path.stat().st_size for path in font_dir.iterdir()) // 1000
    print(f"  {'Updated' if changed else 'Unchanged'}: {font_dir} ({size} kb)")  # noqa: T201

    local_url = f'/{module_path.name}/{css_path.relative_to(module_path).as_posix()}'
    return (
        f"    '{name}': (\n"
        f"        'family': ('{name}', sans-serif),\n"
        f"        'local-url': '{local_url}',\n"
        f"    ),\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[1], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'families', nargs='*',
        help="Google Fonts family specifications (default: the fonts of `$o-theme-font-configs`)",
    )
    parser.add_argument(
        '--module', type=Path, default=WEBSITE_PATH,
        help="path of the module to store the fonts in (default: website)",
    )
    parser.add_argument(
        '--subsets',
        help="comma-separated subsets to keep, as named by Google (default: all of them)",
    )
    args = parser.parse_args()

    module_path = args.module.resolve()
    if not (module_path / '__manifest__.py').is_file():
        sys.exit(f"{module_path} is not a module.")
    families = args.families or default_families(module_path)
    if not families:
        sys.exit(f"No font to download in {primary_variables_path(module_path)}.")
    subsets = set(args.subsets.split(',')) if args.subsets else None

    configs = [download_font(spec, subsets, module_path) for spec in families]
    print("\nDeclare the fonts in $o-theme-font-configs (adapt the generic families):\n")  # noqa: T201
    print(''.join(configs))  # noqa: T201


if __name__ == '__main__':
    main()
