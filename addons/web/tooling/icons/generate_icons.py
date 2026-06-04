#!/usr/bin/env python3

"""
Utility script to generate optimized subsets of the Material Symbols icons
for Odoo.

Two-stage pipeline:

1. **Download** — fetch a variable WOFF2 subset for the requested icons from the
   Google Fonts API (both *Outlined* and *Sharp* variants).

2. **Process** — instantiate two static builds (FILL=0 and FILL=1), detect which
   icons have a distinct filled shape, strip unused glyphs with fontext, and
   merge both builds into a single optimized WOFF2.  Filled glyphs use a ``_f``
   suffix on the ligature sequence::

       "home"   → outlined glyph
       "home_f" → filled glyph

This eliminates the need to keep full source fonts in the repository.

Outputs
-------
* ``static/src/libs/materialsymbols/material_symbols_outlined_subset.woff2``
* ``static/src/libs/materialsymbols/material_symbols_sharp_subset.woff2``
* ``static/src/libs/materialsymbols/material_symbols_{outlined,sharp}.css``
* ``html_editor/.../ms_icons.js``  — icon list with fill-variant flags

Usage
-----
::

    python3 generate_icons.py

Dependencies
------------
::

    pip install fonttools brotli
"""

import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from copy import deepcopy
from io import BytesIO
from pathlib import Path

try:
    from fontTools.misc.transform import Transform
    from fontTools.pens import recordingPen, ttGlyphPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer as vl_instancer
except ImportError as exc:
    msg = (
        "fontTools is required.\n"
        "Install with:  pip install fonttools brotli"
    )
    raise SystemExit(msg) from exc


def load_wishlist() -> list[str]:
    wishlist_path = Path(__file__).resolve().parent / 'icons_wishlist.txt'
    if not wishlist_path.is_file():
        sys.exit(f"Wishlist not found: {wishlist_path}")
    with wishlist_path.open(encoding='utf-8') as fh:
        return sorted(line.strip() for line in fh if line.strip() and not line.startswith('#'))


def fetch_google_font(style: str, icon_names: list[str]) -> bytes:
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

    font_url = match.group(1)
    with urllib.request.urlopen(font_url, timeout=60) as resp:
        return TTFont(BytesIO(resp.read()), recalcBBoxes=False, recalcTimestamp=False)


def _lig4_subtables(lookup) -> list:
    """Return type-4 LigatureSubst subtables from *lookup*, unwrapping Extension wrappers."""
    result = []
    for st in lookup.SubTable:
        real = getattr(st, 'ExtSubTable', st)
        if getattr(real, 'LookupType', None) == 4:
            result.append(real)
    return result


def iter_lig4_subtables(font: TTFont):
    """Yield all type-4 LigatureSubst subtables in *font*, unwrapping Extension wrappers."""
    gsub = font.get('GSUB')
    if not gsub:
        return
    for lookup in gsub.table.LookupList.Lookup:
        yield from _lig4_subtables(lookup)


def detect_filled_variants(font0: TTFont, font1: TTFont, glyphs_map: dict) -> set:
    """Return the subset of icon_names whose glyph outline actually differs
    between FILL=0 (font0) and FILL=1 (font1).

    Icons like ``add``, ``close``, ``check`` are pure geometric shapes whose
    outlines don't change with the FILL axis — we skip the filled glyph copy
    for those so we don't bloat the font with duplicate glyph data.
    """
    gs0 = font0.getGlyphSet()
    gs1 = font1.getGlyphSet()
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


def real_subtables(lookup):
    """Yield (lookup_type, subtable), unwrapping type-7 Extension lookups."""
    if lookup.LookupType == 7:
        for sub in lookup.SubTable:
            yield sub.ExtSubTable.LookupType, sub.ExtSubTable
    else:
        for sub in lookup.SubTable:
            yield lookup.LookupType, sub


def apply_liga(sub, seq: list) -> list:
    if not seq or not hasattr(sub, 'ligatures') or seq[0] not in sub.ligatures:
        return seq
    for lig in sub.ligatures[seq[0]]:
        comp = list(lig.Component)
        if seq[1:1 + len(comp)] == comp:
            return [lig.LigGlyph] + list(seq[1 + len(comp):])
    return seq


def resolve_icons(font, icon_names: list[str]) -> dict[str, str]:
    """Return {icon_name: glyph_name} by tracing each name through GSUB.

    Uses a two-pass strategy:

    1. **Type-4 only** (ligature substitutions) — resolves to the base variable
       glyph (``uniE87D``, ``uniE88A`` …) that retains the FILL axis variation
       in ``gvar``.  Preferred because the FILL variation data is needed to
       produce distinct outlined / filled glyphs.

    2. **Full chain** (type-1 + type-4) — fallback for icons whose sequence
       cannot be resolved by ligature lookup alone.  Type-1 (single
       substitution) in Material Symbols fonts maps outlined glyphs to their
       pre-baked solid counterparts; applying it unconditionally would discard
       the FILL variation data we need.
    """
    gsub = font['GSUB'].table
    cmap = font.getBestCmap()

    def _run(name, *, use_type1: bool):
        seq = [cmap.get(ord(c)) for c in name.replace('-', '_')]
        if None in seq:
            return None
        for lookup in gsub.LookupList.Lookup:
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
        # Prefer type-4-only result — it keeps the variable glyph whose FILL
        # axis variation lets us generate distinct outlined / filled glyphs.
        g = _run(name, use_type1=False)
        if g is None:
            # Cannot resolve with ligatures alone; fall back to full chain.
            g = _run(name, use_type1=True)
        if g is not None:
            results[name] = g
    return results


def add_suffix_to_symbols(font: TTFont, suffix: str) -> TTFont:
    """
    Appends `suffix` to the input string of every ligature in the font
    (GSUB type-4, including Extension-wrapped type-6 lookups).

    E.g. with suffix="_f", the ligature that fires on "home" will instead
    fire on "home_f", leaving the result glyph name unchanged.

    The font must already contain glyphs for every character in `suffix`
    (e.g. glyphs named "underscore" and "f" for "_f").
    """
    cmap = font.getBestCmap()
    suffix_glyphs = []
    for ch in suffix:
        cp = ord(ch)
        glyph_name = cmap.get(cp)
        if glyph_name is None:
            raise ValueError(
                f"No glyph found for character {ch!r} (U+{cp:04X}) in font. "
                f"The font must contain all characters in the suffix.",
            )
        suffix_glyphs.append(glyph_name)

    for subtable in iter_lig4_subtables(font):
        for lig_set in subtable.ligatures.values():
            for lig in lig_set:
                lig.Component = lig.Component + suffix_glyphs

    return font


def redraw_font_glyphs(
    font: TTFont,
    glyph_src_map: dict[str, tuple[TTFont, str]],
) -> None:
    """Redraw every icon glyph using the target font's contours, precisely
    center-aligned to the source glyph with a uniform global scale.
    """
    # 1. Restore UPM and vertical metrics if needed
    src_upm = next(iter(glyph_src_map.values()))[0]['head'].unitsPerEm if glyph_src_map else None
    if src_upm and src_upm != font['head'].unitsPerEm:
        ratio = src_upm / font['head'].unitsPerEm
        font['head'].unitsPerEm = src_upm
        for tag, attrs in (
            ('hhea', ('ascent', 'descent', 'lineGap')),
            ('OS/2', ('sTypoAscender', 'sTypoDescender', 'sTypoLineGap',
                      'usWinAscent', 'usWinDescent',
                      'sxHeight', 'sCapHeight')),
        ):
            tbl = font.get(tag)
            if tbl:
                for attr in attrs:
                    v = getattr(tbl, attr, None)
                    if v is not None:
                        setattr(tbl, attr, round(v * ratio))

    glyf_table = font['glyf']
    hmtx_table = font['hmtx']
    glyph_set = font.getGlyphSet()

    # Use a fixed scale factor to keep visual sizing consistent across all glyphs.
    # Found by trial and error
    scale = 1.153

    for name in font.getGlyphOrder():
        target_glyph = glyf_table[name]
        if target_glyph.numberOfContours == 0:
            continue

        src_info = glyph_src_map.get(name)
        if src_info is None:
            continue

        src_font, src_glyph_name = src_info
        src_glyph = src_font['glyf'][src_glyph_name]

        # 2. Find the exact geometric centers of both glyphs
        src_cx = (src_glyph.xMax + src_glyph.xMin) / 2
        tgt_cx = (target_glyph.xMax + target_glyph.xMin) / 2

        # 3. Calculate translation to align the centers perfectly AFTER scaling
        dx = src_cx - (tgt_cx * scale)
        dy = 0

        # 4. Apply the matrix transformation directly (Scale X, Shear, Shear, Scale Y, Move X, Move Y)
        tt_pen = ttGlyphPen.TTGlyphPen(glyf_table)
        transform = Transform(scale, 0, 0, scale, dx, dy)
        transform_pen = TransformPen(tt_pen, transform)

        glyph_set[name].draw(transform_pen)
        glyf_table[name] = tt_pen.glyph()

        # 5. Overwrite the metrics with the exact source metrics
        hmtx_table[name] = src_font['hmtx'].metrics[src_glyph_name]


def concat_fonts(
    font0: TTFont,
    font1: TTFont,
    glyph_src_map: dict[str, tuple[TTFont, str]] | None = None,
) -> TTFont:
    """
    Merge font_b into font_a and return font_a.

    - All glyphs from font_b are copied into font_a (skipping duplicates).
    - All GSUB LigatureSubst (type-4) lookups from font_b are prepended
        to font_a's GSUB LookupList so that font_b's (longer) sequences
        are tried before font_a's and are not pre-empted by a shorter match.
    - cmap entries from font_b are merged into font_a (font_a wins on conflict).
    - glyph_src_map maps every renamed subset glyph (e.g. ``glyph00011``) to
      ``(source_font, glyph_name_in_source)``.  For outline glyphs the source is
      the FILL=0 instantiation; for filled glyphs the FILL=1 instantiation.
      Each glyph is redrawn from its source through a uniform 1.2x scale so
      that fontext coordinate distortions are discarded entirely.
    """
    glyph_order_a = set(font0.getGlyphOrder())

    # 1. Copy glyphs from font_b that don't already exist in font_a
    new_glyphs = [name for name in font1.getGlyphOrder()
                  if name not in glyph_order_a]

    for name in new_glyphs:
        font0["glyf"].glyphs[name] = deepcopy(font1["glyf"].glyphs[name])
        font0["hmtx"].metrics[name] = font1["hmtx"].metrics[name]
        if "gvar" in font1 and "gvar" in font0 and name in font1["gvar"].variations:
            font0["gvar"].variations[name] = deepcopy(
                font1["gvar"].variations[name])

    font0.setGlyphOrder(font0.getGlyphOrder() + new_glyphs)

    # 2. Prepend GSUB ligature lookups from font_b into font_a
    # font_b's ligatures must come *before* font_a's in the lookup list so that
    # longer sequences (e.g. "home_f") are tried first and not pre-empted by a
    # shorter prefix match (e.g. "home") from font_a.
    gsub_a = font0.get("GSUB")
    gsub_b = font1.get("GSUB")

    if gsub_b and gsub_a:
        lookups_a = gsub_a.table.LookupList.Lookup
        lookups_b = gsub_b.table.LookupList.Lookup

        # Collect type-4 lookups from font_b (unwrapping extensions)
        new_lookups = []
        for lookup in lookups_b:
            for subtable in lookup.SubTable:
                real = getattr(subtable, "ExtSubTable", subtable)
                if real.LookupType == 4:
                    new_lookups.append(deepcopy(lookup))
                    break

        n_new = len(new_lookups)
        if n_new:
            # Shift all existing feature-record indices to make room for the
            # n_new lookups that will occupy positions 0..n_new-1.
            for feature_record in gsub_a.table.FeatureList.FeatureRecord:
                feature = feature_record.Feature
                feature.LookupListIndex = [
                    i + n_new for i in feature.LookupListIndex]

            # Prepend font_b's lookups so they are applied first.
            lookups_a[:] = new_lookups + list(lookups_a)

            # Add the new indices to every FeatureRecord that already references
            # a type-4 lookup from font_a (now shifted by n_new).
            new_indices = list(range(n_new))
            for feature_record in gsub_a.table.FeatureList.FeatureRecord:
                feature = feature_record.Feature
                if any(
                    any(getattr(getattr(st, "ExtSubTable", st), "LookupType", None) == 4
                        for st in lookups_a[i].SubTable)
                    for i in feature.LookupListIndex
                ):
                    for idx in new_indices:
                        if idx not in feature.LookupListIndex:
                            feature.LookupListIndex.append(idx)

    redraw_font_glyphs(font0, glyph_src_map or {})
    return font0


def build_optimized_subset(
    font: TTFont,
    icons: list[str],
):
    input_path = Path(tempfile.gettempdir()) / 'temp_font.woff2'
    output_path = input_path.with_suffix('.out.woff2')
    font.save(input_path)

    subprocess.call([
        "npx", "fontext",
        "-l", ",".join(icons),
        "-i", str(input_path),
        "-o", str(output_path.parent),
        "-n", str(output_path.stem),
        "-f", "woff2",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    res_font = TTFont(output_path)

    input_path.unlink(missing_ok=True)
    # output_path.unlink(missing_ok=True)

    return res_font


def strip_font_metadata(font: TTFont, style: str) -> None:
    """Remove glyph names and unnecessary name records to reduce WOFF2 size.

    - Switches ``post`` to format 3.0: eliminates the ~9 KB glyph-name string
      table (unused in a web icon font) and replaces it with a 32-byte header.
    - Rewrites the ``name`` table to four essential records (nameIDs 1, 2, 4,
      6), deduplicates entries copied from both merged fonts, and replaces the
      ``'temp_font.out'`` artifact left by fontext with a proper family name.
    """
    family = f"Material Symbols {style}"
    ps_name = f"MaterialSymbols{style}-Regular"

    post = font.get('post')
    if post:
        post.formatType = 3.0

    name_table = font.get('name')
    if name_table:
        keep = {
            1: family,
            2: "Regular",
            4: f"{family} Regular",
            6: ps_name,
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


def build_font(
    style: str,
    ms_dir: Path,
    wishlist: list[str],
) -> tuple[set, int]:
    print(f"Building {style} font…")  # noqa: T201
    print("  Downloading font from Google…")  # noqa: T201
    font = fetch_google_font(style, wishlist)

    print("  Resolving icons glyphs…")  # noqa: T201
    glyphs_map = resolve_icons(font, wishlist)
    skipped = [n for n in set(wishlist) if n not in glyphs_map]
    if skipped:
        print("%d icons could not be resolved: %s" % (len(skipped), skipped))  # noqa: T201

    print("  Detecting filled variants…")  # noqa: T201
    font_fill = vl_instancer.instantiateVariableFont(font, {'FILL': 1})
    font_outline = vl_instancer.instantiateVariableFont(font, {'FILL': 0})

    icons_with_fill = detect_filled_variants(
        font_outline, font_fill, glyphs_map)
    fill_suffix = "_f"
    icons_suffixed = [i + fill_suffix for i in icons_with_fill]
    font_fill = add_suffix_to_symbols(font_fill, fill_suffix)

    print("  Optimizing font (ignore the next warnings)…")  # noqa: T201
    stripped_outline = build_optimized_subset(font_outline, list(glyphs_map))
    stripped_fill = build_optimized_subset(font_fill, icons_suffixed)

    # fontext renames glyphs (e.g. add_reaction → glyph00011).  Build a map
    # from each stripped glyph name to its clean reference source so that
    # concat_fonts can redraw every glyph from the correct instantiation
    # rather than from the fontext-distorted coordinates.
    stripped_out_map = resolve_icons(stripped_outline, list(glyphs_map))
    stripped_fill_map = resolve_icons(stripped_fill, icons_suffixed)

    glyph_src_map: dict[str, tuple] = {}
    for icon, strip_name in stripped_out_map.items():
        if icon in glyphs_map:
            glyph_src_map[strip_name] = (font_outline, glyphs_map[icon])
    for icon_f, strip_name in stripped_fill_map.items():
        icon = icon_f[:-len(fill_suffix)]
        if icon in glyphs_map:
            # Metrics (advance width, xMin) are identical between FILL=0 and
            # FILL=1 in Material Symbols; only the contour shapes differ.
            glyph_src_map[strip_name] = (font_fill, glyphs_map[icon])

    merged = concat_fonts(stripped_outline, stripped_fill, glyph_src_map=glyph_src_map)

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
        f"    font-family: 'material_symbols_{style_lower}';\n"
        "    font-style: normal;\n"
        "    font-weight: 400;\n"
        "    font-display: block;\n"
        "    /* This font is a subset of the Material Symbols icons */\n"
        f"    src: url('/web/static/src/libs/materialsymbols/{font_file}') format('woff2');\n"
        "}\n"
    )
    (ms_dir / f'material_symbols_{style_lower}.css').write_text(css, encoding='utf-8')


def write_js_icon_list(dst_path: Path, icons: dict[str, bool]) -> None:
    with urllib.request.urlopen("https://fonts.google.com/metadata/icons?key=material_symbols&incomplete=true", timeout=30) as response:
        response_text = response.read().decode("utf-8")

    # Remove the prefix before passing to json.loads()
    if response_text.startswith(")]}'"):
        clean_data = response_text.replace(")]}'", "", 1)
    result = json.loads(clean_data)
    for icon_data in result.get('icons', []):
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
    """Subset and optimize Material Symbols fonts for the web module.

    Downloads variable subsets from Google Fonts (no local source fonts needed),
    instantiates FILL=0 and FILL=1 static builds, strips unused glyphs, and
    merges them into a single WOFF2 per style variant.

    Run once whenever the wishlist changes:

        python3 generate_icons.py

    Requires:

        pip install fonttools brotli
    """
    script_path = Path(__file__).resolve()

    module_path = script_path.parent.parent.parent  # .../web/tooling/icons → .../web
    if not module_path.exists():
        sys.exit("Could not locate the 'web' module.")

    ms_dir = module_path / 'static' / 'src' / 'libs' / 'materialsymbols'

    wishlist = load_wishlist()

    icons, outline_path = build_font("Outlined", ms_dir, wishlist)
    _, sharp_path = build_font("Sharp", ms_dir, wishlist)

    write_js_icon_list(
        module_path.parent / 'html_editor' / 'static' / 'src' / 'main' / 'media' / 'media_dialog' / 'data' / 'ms_icons.js',
        icons,
    )

    n_filled = sum(1 for filled in icons.values() if filled)
    print(  # noqa: T201
        f"\n✓  Generated fonts with {len(icons)} icons ({n_filled} with filled variant)\n"
        f"   outlined  → {outline_path}  ({outline_path.stat().st_size // 1000} kb)\n"
        f"   sharp     → {sharp_path}  ({sharp_path.stat().st_size // 1000} kb)\n",
    )


if __name__ == "__main__":
    main()
