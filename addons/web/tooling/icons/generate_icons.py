#!/usr/bin/env python3

"""
Generate optimized subsets of the Material Symbols icons for Odoo.

Two-stage pipeline:

1. **Download** — fetch a variable WOFF2 subset for the icons listed in
   ``icons_wishlist.txt`` from the Google Fonts API (*Outlined* and *Sharp*).

2. **Process** — instantiate two static builds (FILL=0 and FILL=1), detect which
   icons have a distinct filled shape, strip unused glyphs with fontext, and
   merge both builds into a single optimized WOFF2.  Filled glyphs get a ``_f``
   suffix on the ligature sequence: ``home`` → outlined, ``home_f`` → filled.

Outputs
-------
* ``static/src/libs/materialsymbols/material_symbols_{outlined,sharp}_subset.woff2``
* ``static/src/libs/materialsymbols/material_symbols_{outlined,sharp}.css``
* ``html_editor/.../ms_icons.js`` — icon list with fill-variant flags

Usage
-----
::

    pip install 'fonttools[pathops]' brotli
    npm install fontext          # or make `npx fontext` resolvable
    python3 generate_icons.py
"""

import json
import logging
import re
import subprocess
import sys
import tempfile
import urllib.request
from copy import deepcopy
from io import BytesIO
from pathlib import Path

try:
    from fontTools.otlLib.builder import buildLigatureSubstSubtable
    from fontTools.pens import recordingPen, transformPen, ttGlyphPen
    from fontTools.ttLib import TTFont, removeOverlaps
    from fontTools.ttLib.tables import otTables
    from fontTools.varLib import instancer as vl_instancer
except ImportError as exc:
    raise SystemExit(
        "fontTools (with the pathops extra) is required.\n"
        "Install with:  pip install 'fonttools[pathops]' brotli",
    ) from exc

FILL_SUFFIX = "_f"

# Material Symbols centers its artwork on the em square, i.e. 50% of the em
# above the baseline, whereas text-adjacent icons need to sit lower to look
# optically aligned with the surrounding text (FontAwesome, the previous icon
# set, centered at ~36%).  Baking the offset into the outlines here means the
# glyphs sit correctly on the text baseline with no stylesheet correction to
# keep in sync (it used to be `vertical-align: -11.5%` on `.oi`/`.mi`/`.fa`).
BASELINE_SHIFT = 0.115

# Material Symbols draw their artwork on a 20x20 area centered in the 24x24
# grid; scaling by 24/20 makes an icon that fills its grid also fill the em
# square, which is the size the rest of the UI is calibrated for.
GLYPH_SCALE = 1.2

# Vertical metrics, per table, that must follow a change of unitsPerEm.
UPM_METRICS = (
    ('hhea', ('ascent', 'descent', 'lineGap')),
    ('OS/2', ('sTypoAscender', 'sTypoDescender', 'sTypoLineGap',
              'usWinAscent', 'usWinDescent', 'sxHeight', 'sCapHeight')),
)

# Vertical metrics that must follow a change of baseline position.
BASELINE_METRICS = (
    ('hhea', ('ascent', 'descent')),
    ('OS/2', ('sTypoAscender', 'sTypoDescender', 'usWinAscent', 'usWinDescent')),
)


def update_metrics(font: TTFont, spec, transform) -> None:
    """Apply *transform* (attr, value) → value to each metric listed in *spec*."""
    for tag, attrs in spec:
        table = font.get(tag)
        if not table:
            continue
        for attr in attrs:
            value = getattr(table, attr, None)
            if value is not None:
                setattr(table, attr, transform(attr, value))


def check_fontext() -> None:
    """Fail early if the `fontext` CLI cannot be run."""
    try:
        proc = subprocess.run(
            ["npx", "--no-install", "fontext", "--version"],
            capture_output=True, text=True, timeout=120, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"Could not run `npx fontext`: {exc}\nInstall with:  npm install fontext") from exc
    if proc.returncode != 0:
        raise SystemExit(
            "fontext is required but not installed.\n"
            "Install with:  npm install fontext\n"
            f"`npx fontext --version` failed:\n{(proc.stderr or proc.stdout).strip()}",
        )


def load_wishlist() -> list[str]:
    wishlist_path = Path(__file__).resolve().parent / 'icons_wishlist.txt'
    if not wishlist_path.is_file():
        sys.exit(f"Wishlist not found: {wishlist_path}")
    with wishlist_path.open(encoding='utf-8') as fh:
        return sorted(line.strip() for line in fh if line.strip() and not line.startswith('#'))


def fetch_google_font(style: str, icon_names: list[str]) -> TTFont:
    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    req = urllib.request.Request(
        "https://fonts.googleapis.com/css2"
        f"?family=Material+Symbols+{style}:opsz,wght,FILL,GRAD@24,400,0..1,0"
        f"&icon_names={','.join(icon_names)}",
        headers={"User-Agent": user_agent},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        css = resp.read().decode("utf-8")

    match = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css)
    if not match:
        raise SystemExit(
            "Could not find a font URL in the Google Fonts CSS response.\n"
            f"Response preview:\n{css[:600]}",
        )

    with urllib.request.urlopen(match.group(1), timeout=60) as resp:
        return TTFont(BytesIO(resp.read()), recalcBBoxes=False, recalcTimestamp=False)


def real_subtables(lookup, lookup_type: int | None = None):
    """Yield (type, subtable) of *lookup*, unwrapping type-7 Extension lookups.

    With *lookup_type* set, only subtables of that type are yielded.
    """
    for sub in lookup.SubTable:
        real = sub.ExtSubTable if lookup.LookupType == 7 else sub
        ltype = real.LookupType if lookup.LookupType == 7 else lookup.LookupType
        if lookup_type is None or ltype == lookup_type:
            yield ltype, real


def iter_subtables(font: TTFont, lookup_type: int | None = None):
    """Yield (type, subtable) for every GSUB subtable of *font*."""
    gsub = font.get('GSUB')
    if not gsub:
        return
    for lookup in gsub.table.LookupList.Lookup:
        yield from real_subtables(lookup, lookup_type)


def detect_filled_variants(font_outline: TTFont, font_fill: TTFont, glyphs_map: dict) -> set:
    """Return the icon names whose outline actually differs between FILL=0 and FILL=1.

    Icons like ``add``, ``close``, ``check`` are pure geometric shapes unaffected
    by the FILL axis; skipping their filled copy avoids duplicate glyph data.
    """
    gs0 = font_outline.getGlyphSet()
    gs1 = font_fill.getGlyphSet()
    has_fill = set()

    for name, glyph_name in glyphs_map.items():
        pen0, pen1 = recordingPen.RecordingPen(), recordingPen.RecordingPen()
        try:
            gs0[glyph_name].draw(pen0)
            gs1[glyph_name].draw(pen1)
        except KeyError:
            has_fill.add(name)   # cannot compare → assume fill exists
            continue
        if pen0.value != pen1.value:
            has_fill.add(name)

    return has_fill


def apply_liga(sub, seq: list) -> list:
    if not seq or not hasattr(sub, 'ligatures') or seq[0] not in sub.ligatures:
        return seq
    for lig in sub.ligatures[seq[0]]:
        comp = list(lig.Component)
        if seq[1:1 + len(comp)] == comp:
            return [lig.LigGlyph] + list(seq[1 + len(comp):])
    return seq


def resolve_icons(font: TTFont, icon_names: list[str]) -> dict[str, str]:
    """Return {icon_name: glyph_name} by tracing each name through GSUB.

    Ligature lookups (type 4) are tried alone first: they resolve to the base
    variable glyph (``uniE87D`` …) which still carries the FILL axis variation
    needed to produce distinct outlined / filled glyphs.  Single substitutions
    (type 1) map outlined glyphs to pre-baked solid ones, discarding that
    variation, so they are only used as a fallback.
    """
    cmap = font.getBestCmap()

    def _run(name, *, use_type1: bool):
        seq = [cmap.get(ord(c)) for c in name.replace('-', '_')]
        if None in seq:
            return None
        for lookup in font['GSUB'].table.LookupList.Lookup:
            changed = True
            while changed:
                changed = False
                for ltype, sub in real_subtables(lookup):
                    if ltype == 1 and use_type1 and hasattr(sub, 'mapping'):
                        new = [sub.mapping.get(g, g) for g in seq]
                        if new != seq:
                            seq = new
                            changed = True
                    elif ltype == 4:
                        new, i = [], 0
                        while i < len(seq):
                            r = apply_liga(sub, seq[i:])
                            if r != seq[i:]:
                                new.extend(r)
                                i = len(seq)
                                changed = True
                            else:
                                new.append(seq[i])
                                i += 1
                        seq = new
        return seq[0] if len(seq) == 1 else None

    results = {}
    for name in icon_names:
        glyph = _run(name, use_type1=False) or _run(name, use_type1=True)
        if glyph is not None:
            results[name] = glyph
    return results


def build_ligatures(font: TTFont, ligatures: dict[str, str]) -> list[str]:
    """Replace every GSUB lookup with a single ligature lookup mapping each name
    in *ligatures* to its glyph, and return the names that could not be encoded.

    Rebuilding the table instead of merging the ones the two subsets came with is
    what makes the icon names unambiguous.  Inside a ligature set the *first*
    match wins, so a name that is a prefix of another must come last
    (``format_image`` after ``format_image_front``, ``close_f`` after
    ``close_fullscreen``).  A merged lookup list cannot express that at all — the
    earlier lookup consumes the sequence before the later one is tried, which is
    how ``alternate_email_f`` ended up drawing ``mail_f`` (matching
    "e-**mail**-_f").  :func:`buildLigatureSubstSubtable` sorts every set
    longest-first, so the shaper always takes the longest match.
    """
    cmap = font.getBestCmap()
    mapping, unencodable = {}, []
    for name, glyph_name in ligatures.items():
        seq = tuple(cmap.get(ord(c)) for c in name)
        if None in seq:
            unencodable.append(name)
            continue
        mapping[seq] = glyph_name

    lookup = otTables.Lookup()
    lookup.LookupType = 4
    lookup.LookupFlag = 0
    lookup.SubTable = [buildLigatureSubstSubtable(mapping)]
    lookup.SubTableCount = 1

    gsub = font['GSUB'].table
    gsub.LookupList.Lookup = [lookup]
    gsub.LookupList.LookupCount = 1
    for feature_record in gsub.FeatureList.FeatureRecord:
        feature_record.Feature.LookupListIndex = [0]
        feature_record.Feature.LookupCount = 1
    return unencodable


def add_suffix_to_symbols(font: TTFont, suffix: str) -> TTFont:
    """Append *suffix* to the input sequence of every ligature in the font.

    With suffix="_f", the ligature firing on "home" fires on "home_f" instead,
    the result glyph being unchanged.  The font must already contain a glyph for
    every character of *suffix*.
    """
    cmap = font.getBestCmap()
    suffix_glyphs = []
    for char in suffix:
        glyph_name = cmap.get(ord(char))
        if glyph_name is None:
            raise ValueError(
                f"No glyph found for character {char!r} (U+{ord(char):04X}) in font. "
                f"The font must contain all characters in the suffix.",
            )
        suffix_glyphs.append(glyph_name)

    for _ltype, subtable in iter_subtables(font, lookup_type=4):
        for lig_set in subtable.ligatures.values():
            for lig in lig_set:
                lig.Component = lig.Component + suffix_glyphs

    return font


def shift_baseline(font: TTFont, shift: int) -> None:
    """Move the font's vertical metrics down by *shift* units.

    The outlines are drawn *shift* units lower than the em-square center (see
    :data:`BASELINE_SHIFT`), so the declared ascender/descender must follow or
    the glyphs would extend below a descent of 0.  Ascent and descent move by the
    same amount, keeping the total line height unchanged — only the baseline
    position within it moves.  usWinDescent is stored as a positive distance
    *below* the baseline, hence the opposite sign.
    """
    update_metrics(
        font, BASELINE_METRICS,
        lambda attr, value: value + shift if attr == 'usWinDescent' else value - shift,
    )


def redraw_font_glyphs(font: TTFont, glyph_src_map: dict[str, tuple[TTFont, str]]) -> None:
    """Redraw every icon glyph scaled by :data:`GLYPH_SCALE` around the design-grid
    center, then lowered by :data:`BASELINE_SHIFT`.

    Outlines are taken from *glyph_src_map* — the pristine FILL=0 / FILL=1
    instantiations — not from the glyphs fontext produced: fontext rescales the
    contours to its own normalized grid and rounds to integers, which visibly
    deforms curves (the circle in the ``sentiment_*`` / ``mood`` faces bulged
    out).  Redrawing from the source discards those coordinates entirely.

    Overlaps are then removed.  Instantiating the FILL axis collapses the
    counters of the outlined shape onto its edges instead of deleting them, so a
    filled glyph keeps overlapping contours with coincident edges (``mail_f``,
    ``cloud_upload_f`` …) whose antialiasing coverage cancels out and shows up as
    thin grooves.  Booleaning them into one shape leaves the fill unchanged.

    The same affine transform is applied to every glyph, which is what keeps the
    set visually consistent: Material Symbols share a 24x24 grid and each icon's
    placement *within* it is deliberate, so any per-glyph correction (e.g.
    centering on the ink bounding box) would destroy the intended alignment.
    """
    # Restore the source UPM and rescale the vertical metrics to match.
    src_upm = next(iter(glyph_src_map.values()))[0]['head'].unitsPerEm if glyph_src_map else None
    if src_upm and src_upm != font['head'].unitsPerEm:
        ratio = src_upm / font['head'].unitsPerEm
        font['head'].unitsPerEm = src_upm
        update_metrics(font, UPM_METRICS, lambda _attr, value: round(value * ratio))

    glyf_table = font['glyf']
    hmtx_table = font['hmtx']
    upm = font['head'].unitsPerEm
    baseline_shift = round(upm * BASELINE_SHIFT)
    glyph_set = font.getGlyphSet()
    src_glyph_sets: dict[int, dict] = {}

    for name in font.getGlyphOrder():
        if glyf_table[name].numberOfContours == 0:
            continue

        src_info = glyph_src_map.get(name)
        if src_info is None:
            continue

        src_font, src_glyph_name = src_info
        src_glyph_set = src_glyph_sets.setdefault(id(src_font), src_font.getGlyphSet())

        # Enlarge around the center of the design grid: the center of the advance
        # box (X) and of the em square lowered by BASELINE_SHIFT (Y).  The grid
        # center — not the glyph's own ink center — is the fixed point, so an icon
        # drawn off-center on purpose (`mobile_off`, `star`, `visibility_off` …)
        # keeps its intended offset.
        advance = src_font['hmtx'].metrics[src_glyph_name][0]
        dx = advance / 2 - advance / 2 * GLYPH_SCALE
        dy = upm / 2 - baseline_shift - upm / 2 * GLYPH_SCALE

        tt_pen = ttGlyphPen.TTGlyphPen(glyf_table)
        transform_pen = transformPen.TransformPen(tt_pen, (GLYPH_SCALE, 0, 0, GLYPH_SCALE, dx, dy))
        src_glyph_set[src_glyph_name].draw(transform_pen)
        new_glyph = tt_pen.glyph()
        glyf_table[name] = new_glyph

        # Keep the source advance width, but set the left side bearing to the
        # actual (scaled, recentered) outline so hmtx matches the glyph.
        new_glyph.recalcBounds(glyf_table)
        hmtx_table[name] = (advance, new_glyph.xMin)

        removeOverlaps.removeTTGlyphOverlaps(name, glyph_set, glyf_table, hmtx_table)

    shift_baseline(font, baseline_shift)


def concat_fonts(
    font_outline: TTFont,
    font_fill: TTFont,
    glyph_src_map: dict[str, tuple[TTFont, str]] | None = None,
) -> TTFont:
    """Merge *font_fill* into *font_outline* and return the latter.

    Glyphs missing from *font_outline* are copied over, then every glyph is
    redrawn from its source in *glyph_src_map* (see :func:`redraw_font_glyphs`).
    The GSUB of neither font is carried over: the name → glyph ligatures are
    rebuilt from scratch by :func:`build_ligatures`.
    """
    known = set(font_outline.getGlyphOrder())
    new_glyphs = [name for name in font_fill.getGlyphOrder() if name not in known]

    for name in new_glyphs:
        font_outline['glyf'].glyphs[name] = deepcopy(font_fill['glyf'].glyphs[name])
        font_outline['hmtx'].metrics[name] = font_fill['hmtx'].metrics[name]
        if 'gvar' in font_fill and 'gvar' in font_outline and name in font_fill['gvar'].variations:
            font_outline['gvar'].variations[name] = deepcopy(font_fill['gvar'].variations[name])

    font_outline.setGlyphOrder(font_outline.getGlyphOrder() + new_glyphs)

    redraw_font_glyphs(font_outline, glyph_src_map or {})
    return font_outline


def build_optimized_subset(font: TTFont, icons: list[str]) -> TTFont:
    """Run fontext on *font*, keeping only the ligatures named in *icons*."""
    with tempfile.TemporaryDirectory(prefix='odoo_icons_') as tmp_dir:
        input_path = Path(tmp_dir) / 'font.woff2'
        output_path = input_path.with_suffix('.out.woff2')
        font.save(input_path)

        try:
            subprocess.run([
                "npx", "--no-install", "fontext",
                "-l", ",".join(icons),
                "-i", str(input_path),
                "-o", str(output_path.parent),
                "-n", str(output_path.stem),
                "-f", "woff2",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as exc:
            raise SystemExit(f"fontext failed:\n{(exc.stderr or b'').decode(errors='replace')}") from exc

        # fontext leaves two stray bytes at the end of the `post` table string
        # data, which makes fontTools warn every time the table gets parsed.
        # Those glyph names are dropped anyway — `strip_font_metadata` rewrites
        # `post` as format 3.0 — so the warning is pure noise here.
        logging.getLogger('fontTools.ttLib.tables._p_o_s_t').setLevel(logging.ERROR)
        # Read into memory so the font outlives the temporary directory.
        return TTFont(BytesIO(output_path.read_bytes()))


def strip_font_metadata(font: TTFont, style: str) -> None:
    """Remove glyph names and unnecessary name records to reduce WOFF2 size.

    - ``post`` becomes format 3.0: the ~9 KB glyph-name string table (unused in a
      web icon font) is replaced by a 32-byte header.
    - ``name`` is reduced to four records (nameIDs 1, 2, 4, 6), deduplicating
      entries copied from both merged fonts and replacing the
      ``'temp_font.out'`` artifact left by fontext with a proper family name.
    """
    family = f"Material Symbols {style}"

    post = font.get('post')
    if post:
        post.formatType = 3.0

    name_table = font.get('name')
    if not name_table:
        return

    keep = {
        1: family,
        2: "Regular",
        4: f"{family} Regular",
        6: f"MaterialSymbols{style}-Regular",
    }
    seen = set()
    new_records = []
    for record in name_table.names:
        if record.nameID not in keep:
            continue
        key = (record.nameID, record.platformID, record.platEncID, record.langID)
        if key in seen:
            continue
        seen.add(key)
        record.string = keep[record.nameID].encode(
            'utf-16-be' if record.isUnicode() else 'latin-1',
            errors='replace',
        )
        new_records.append(record)
    name_table.names = new_records


def build_font(style: str, ms_dir: Path, wishlist: list[str]) -> tuple[dict, Path]:
    print(f"Building {style} font…")  # noqa: T201
    print("  Downloading font from Google…")  # noqa: T201
    font = fetch_google_font(style, wishlist)

    print("  Resolving icons glyphs…")  # noqa: T201
    glyphs_map = resolve_icons(font, wishlist)
    skipped = [n for n in set(wishlist) if n not in glyphs_map]
    if skipped:
        print(f"  {len(skipped)} icons could not be resolved: {sorted(skipped)}")  # noqa: T201

    print("  Detecting filled variants…")  # noqa: T201
    font_fill = vl_instancer.instantiateVariableFont(font, {'FILL': 1})
    font_outline = vl_instancer.instantiateVariableFont(font, {'FILL': 0})

    icons_with_fill = detect_filled_variants(font_outline, font_fill, glyphs_map)
    icons_suffixed = [i + FILL_SUFFIX for i in icons_with_fill]
    font_fill = add_suffix_to_symbols(font_fill, FILL_SUFFIX)

    print("  Optimizing font…")  # noqa: T201
    stripped_outline = build_optimized_subset(font_outline, list(glyphs_map))
    stripped_fill = build_optimized_subset(font_fill, icons_suffixed)

    # fontext renames glyphs (e.g. add_reaction → glyph00011), so ask each subset
    # which glyph its icon names ended up on.  Key the answer by the *source*
    # glyph rather than by icon name: fontext keeps a single ligature per glyph,
    # so of two names sharing one glyph (``help`` / ``help_outline``,
    # ``chevron_left`` / ``chevron_backward`` …) only one survives, and going
    # through the source glyph gives the dropped alias its glyph back.
    outline_glyph = {
        glyphs_map[icon]: glyph
        for icon, glyph in resolve_icons(stripped_outline, list(glyphs_map)).items()
    }
    fill_glyph = {
        glyphs_map[icon[:-len(FILL_SUFFIX)]]: glyph
        for icon, glyph in resolve_icons(stripped_fill, icons_suffixed).items()
    }

    # Redraw every glyph from the pristine instantiation it came from rather than
    # from the coordinates fontext produced.  Metrics (advance width, xMin) are
    # identical between FILL=0 and FILL=1; only the contour shapes differ.
    glyph_src_map = {
        **{glyph: (font_outline, src) for src, glyph in outline_glyph.items()},
        **{glyph: (font_fill, src) for src, glyph in fill_glyph.items()},
    }
    merged = concat_fonts(stripped_outline, stripped_fill, glyph_src_map=glyph_src_map)

    # Both the plain and the `_f` name of every icon must resolve.  Icons whose
    # shape doesn't change with FILL (``add``, ``close`` …) have no filled glyph,
    # so their `_f` name points back at the outlined one: a suffix with no
    # ligature behind it doesn't render the outlined icon, it lets the shaper
    # match whatever it can find inside the name instead.
    ligatures = {}
    unresolved = []
    for icon, src in glyphs_map.items():
        if src not in outline_glyph:
            unresolved.append(icon)
            continue
        ligatures[icon] = outline_glyph[src]
        ligatures[icon + FILL_SUFFIX] = fill_glyph.get(src, outline_glyph[src])

    unresolved += build_ligatures(merged, ligatures)
    if unresolved:
        print(f"  {len(unresolved)} icons could not be encoded: {sorted(unresolved)}")  # noqa: T201

    strip_font_metadata(merged, style)

    print("  Saving font…")  # noqa: T201
    ms_dir.mkdir(parents=True, exist_ok=True)
    output_font_path = ms_dir / f'material_symbols_{style.lower()}_subset.woff2'
    merged.save(output_font_path)
    write_font_face_css(ms_dir, style.lower(), output_font_path.name)

    icons = {name: {'has_fill': name in icons_with_fill} for name in wishlist if name in glyphs_map}
    return icons, output_font_path


def write_font_face_css(ms_dir: Path, style_lower: str, font_file: str) -> None:
    css = (
        "/* Generated by `odoo/addons/web/tooling/icons/generate_icons.py` — do not edit manually. */\n"
        "@font-face {\n"
        f"    font-family: 'Material Symbols {style_lower.capitalize()}';\n"
        "    font-style: normal;\n"
        "    font-weight: 400;\n"
        "    font-display: block;\n"
        "    /* This font is a subset of the Material Symbols icons */\n"
        f"    src: url('/web/static/src/libs/materialsymbols/{font_file}') format('woff2');\n"
        "}\n"
    )
    (ms_dir / f'material_symbols_{style_lower}.css').write_text(css, encoding='utf-8')


def write_js_icon_list(dst_path: Path, icons: dict[str, dict]) -> None:
    url = "https://fonts.google.com/metadata/icons?key=material_symbols&incomplete=true"
    with urllib.request.urlopen(url, timeout=30) as response:
        response_text = response.read().decode("utf-8")

    # The response is prefixed with an anti-JSON-hijacking guard.
    metadata = json.loads(response_text.removeprefix(")]}'"))
    for icon_data in metadata.get('icons', []):
        if icon_data['name'] in icons:
            icons[icon_data['name']]['tags'] = ' '.join(icon_data.get('tags', []))

    entries = ',\n    '.join(
        f'{icon_name}: {{\n'
        f'        has_fill: {"true" if icon["has_fill"] else "false"},\n'
        f'        tags: "{icon.get("tags", "")}",\n'
        f'    }}'
        for icon_name, icon in icons.items()
    )
    dst_path.write_text(
        "/**\n"
        " * Generated by `odoo/addons/web/tooling/icons/generate_icons.py` — do not edit\n"
        " * manually.\n"
        " * This object contains the Material Symbols icons that Odoo uses.\n"
        " */\n"
        f"const MS_ICONS = {{\n    {entries},\n}};\n\n"
        "export default MS_ICONS;\n",
        encoding='utf-8',
    )


def main() -> None:
    check_fontext()

    module_path = Path(__file__).resolve().parents[2]  # .../web/tooling/icons → .../web
    if not module_path.exists():
        sys.exit("Could not locate the 'web' module.")

    ms_dir = module_path / 'static' / 'src' / 'libs' / 'materialsymbols'
    wishlist = load_wishlist()

    icons, outline_path = build_font("Outlined", ms_dir, wishlist)
    _, sharp_path = build_font("Sharp", ms_dir, wishlist)

    write_js_icon_list(
        module_path.parent / 'html_editor' / 'static' / 'src' / 'main' / 'media' / 'media_dialog' / 'ms_icons.js',
        icons,
    )

    n_filled = sum(1 for icon in icons.values() if icon['has_fill'])
    print(  # noqa: T201
        f"\n✓  Generated fonts with {len(icons)} icons ({n_filled} with filled variant)\n"
        f"   outlined  → {outline_path}  ({outline_path.stat().st_size // 1000} kb)\n"
        f"   sharp     → {sharp_path}  ({sharp_path.stat().st_size // 1000} kb)\n",
    )


if __name__ == "__main__":
    main()
