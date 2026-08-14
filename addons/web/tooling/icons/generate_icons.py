#!/usr/bin/env python3

"""
Generate optimized subsets of the Material Symbols icons for Odoo.

Two-stage pipeline:

1. **Download** — fetch a variable WOFF2 subset for the icons listed in
   ``icons_wishlist.txt`` from the Google Fonts API (*Outlined* and *Sharp*).

2. **Process** — instantiate two static builds (FILL=0 and FILL=1), detect which
   icons have a distinct filled shape, strip unused glyphs with fontext, and
   merge both builds into a single optimized WOFF2.  The web fonts are reached
   by ligature only — their cmap keeps just the ASCII characters the icon names
   are spelled with — so a filled glyph comes either from the ``FILL`` variation
   axis (``home`` + ``font-variation-settings: 'FILL' 1``), which is what
   ``.oi-filled`` uses, or from a ``_f`` suffix on the ligature sequence
   (``home_f``), kept for the stylesheets that spell the filled name out in a
   ``content`` declaration.

   A third font is cloned off the outlined build for the backend — wkhtmltopdf,
   which cannot read WOFF2, and the Pillow PNG renderer of the mail icons — as a
   WOFF with the same glyphs and ligatures, plus the icon codepoints in its cmap:
   Pillow has no shaper to resolve a ligature with (see
   :func:`build_backend_font`).

Outputs
-------
* ``static/src/libs/materialsymbols/material_symbols_{outlined,sharp}_subset.woff2``
* ``static/src/libs/materialsymbols/material_symbols_{outlined,sharp}.css``
* ``static/src/libs/materialsymbols/material_symbols_backend.woff`` — outlined font for
  wkhtmltopdf and PIL
* ``html_editor/controllers/ms_icons.py`` — icon list with fill-variant flags, codepoints for
  PIL and search tags

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
    from fontTools.otlLib.builder import (
        buildLigatureSubstSubtable,
        buildStatTable,
    )
    from fontTools.pens import recordingPen, transformPen, ttGlyphPen
    from fontTools.ttLib import TTFont, newTable, removeOverlaps
    from fontTools.ttLib.tables import otTables
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
    from fontTools.ttLib.tables._f_v_a_r import Axis
    from fontTools.varLib import instancer as vl_instancer
    from fontTools.varLib.featureVars import addFeatureVariations
except ImportError as exc:
    raise SystemExit(
        "fontTools (with the pathops extra) is required.\n"
        "Install with:  pip install 'fonttools[pathops]' brotli",
    ) from exc

from fontTools.misc import timeTools

FILL_SUFFIX = "_f"

# Font the server renders with: wkhtmltopdf cannot read WOFF2, and Pillow needs
# the icon codepoints (see :func:`build_backend_font`).  Only the outlined style
# is ever rendered server-side.
BACKEND_FONT_FILE = "material_symbols_backend.woff"

# The merged font advertises the same FILL axis as the upstream variable font, so
# that `.oi-filled` can reach the filled artwork with `font-variation-settings`
# instead of appending FILL_SUFFIX to the ligature name (which needs two `content`
# items, and Firefox charges the advance of a ligature straddling them twice).
#
# The axis is *not* backed by glyph variations: no `gvar` is emitted, only `fvar`
# plus a GSUB condition swapping the outlined glyph for the filled one above
# FILL_THRESHOLD.  The switch is a snap, not an interpolation, which is what keeps
# the two pre-baked glyph sets and the overlap removal of
# :func:`redraw_font_glyphs` (interpolating would require the FILL=1 counters
# collapsed onto the edges, and those show up as thin grooves under antialiasing).
FILL_AXIS = "FILL"
FILL_THRESHOLD = 0.5

# Feature carrying the conditional substitution.  It must be applied *after*
# `liga`, otherwise there is no icon glyph to swap yet: HarfBuzz runs `rvrn` in
# its preprocessing stage, before the ligature fires.  `rclt` runs in the same
# stage as `liga`, is on by default, and no stylesheet would think of disabling it.
FILL_FEATURE = "rclt"

# Codepoint of the filled artwork, as an offset in the Plane-16 Private Use Area.
#
# Pillow renders the icons for mail (see `_get_icon_rendering_info`) with FreeType
# alone, no RAQM/HarfBuzz, so it can only reach a glyph through the cmap of the
# backend font: no ligature to resolve `home`, and no FILL axis either, that one
# being backed by a GSUB substitution rather than by glyph variations (see
# :func:`add_fill_axis`).  The outlined glyphs keep the codepoints Google assigns
# them, so that the generated mapping is upstream's and stays stable when an icon
# is added; the filled ones have none and get one here.
#
# The low word of the outlined codepoint is mirrored into Plane 16 rather than
# offset by a constant, because no single offset keeps every filled codepoint
# inside a Private Use block: Google's codepoints sit in the BMP PUA
# (U+E000..U+F8FF) but a few land near the end of the Plane-15 PUA
# (U+FFF9A `horizontal_align_right` …), and those two ranges leave no common
# slack.  Masking sidesteps it: BMP codepoints land in U+10E000..U+10F8FF and the
# Plane-15 ones in U+10FF9A.., which cannot collide.
FILL_CODEPOINT_PLANE = 0x100000
# Free codepoints for the rare icon Google leaves out of its own cmap.
PUA_START = 0xE000
PUA_END = 0xF8FF

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

    # `close_small` is wrongly detected as having a filled variant
    has_fill.discard("close_small")

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


def make_feature_record(tag: str, lookup_indices: list[int]) -> otTables.FeatureRecord:
    feature = otTables.Feature()
    feature.FeatureParams = None
    feature.LookupListIndex = lookup_indices
    feature.LookupCount = len(lookup_indices)
    record = otTables.FeatureRecord()
    record.FeatureTag = tag
    record.Feature = feature
    return record


def build_gsub(font: TTFont, ligatures: dict[str, str]) -> list[str]:
    """Rebuild the GSUB table from scratch and return the names that could not be
    encoded.

    A single ``liga`` lookup is emitted, mapping each name in *ligatures* to its
    glyph.  :func:`add_fill_axis` appends its own lookup afterwards, so that the
    shaper resolves the name before swapping the artwork.

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

    liga_lookup = otTables.Lookup()
    liga_lookup.LookupType = 4
    liga_lookup.LookupFlag = 0
    liga_lookup.SubTable = [buildLigatureSubstSubtable(mapping)]
    liga_lookup.SubTableCount = 1

    lookups = [liga_lookup]
    features = [make_feature_record('liga', [0])]

    gsub = font['GSUB'].table
    gsub.LookupList.Lookup = lookups
    gsub.LookupList.LookupCount = len(lookups)
    gsub.FeatureList.FeatureRecord = features
    gsub.FeatureList.FeatureCount = len(features)
    for script_record in gsub.ScriptList.ScriptRecord:
        script = script_record.Script
        lang_systems = [r.LangSys for r in script.LangSysRecord]
        if script.DefaultLangSys:
            lang_systems.append(script.DefaultLangSys)
        for lang_sys in lang_systems:
            lang_sys.FeatureIndex = list(range(len(features)))
            lang_sys.FeatureCount = len(features)
    return unencodable


def add_fill_axis(font: TTFont, filled_glyphs: dict[str, str]) -> None:
    """Turn *font* into a variable font whose only axis snaps between the outlined
    and the filled artwork (see :data:`FILL_AXIS`).

    ``fvar`` declares the axis and ``STAT`` names its two ends — both are needed
    for the font to be recognized as variable — while a GSUB FeatureVariations
    condition substitutes each outlined glyph of *filled_glyphs* for its filled
    counterpart once the axis passes :data:`FILL_THRESHOLD`.

    Must run *after* :func:`strip_font_metadata`, which would drop the name
    records ``fvar``/``STAT`` point at.
    """
    if not filled_glyphs:
        return

    axis = Axis()
    axis.axisTag = FILL_AXIS
    axis.minValue, axis.defaultValue, axis.maxValue = 0, 0, 1
    axis.axisNameID = font['name'].addMultilingualName({'en': "Fill"}, font, minNameID=255)

    fvar = newTable('fvar')
    fvar.axes = [axis]
    # No named instances: nothing consumes them, and each costs a name record.
    fvar.instances = []
    font['fvar'] = fvar

    buildStatTable(font, [{
        'tag': FILL_AXIS,
        'name': "Fill",
        'values': [
            {'value': 0, 'name': "Outlined", 'flags': 0x2},  # ElidableAxisValueName
            {'value': 1, 'name': "Filled"},
        ],
    }])

    addFeatureVariations(
        font,
        [([{FILL_AXIS: (FILL_THRESHOLD, 1)}], filled_glyphs)],
        featureTag=FILL_FEATURE,
    )


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
        return TTFont(BytesIO(output_path.read_bytes()), recalcTimestamp=False)


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


def compile_font(font: TTFont) -> bytes:
    buffer = BytesIO()
    font.save(buffer)
    return buffer.getvalue()


def save_font(font: TTFont, path) -> None:
    """Write *font* to *path*, dating it only if its content actually changed.

    fontext stamps the current time into ``head``, so an unchanged rebuild would
    still write a different file and make the binary diff of the subsets say
    nothing about the icons.  The existing file is therefore compared against the
    new one with both dates equalized, and left untouched when they match --
    ``created`` is kept for the lifetime of the file, only ``modified`` follows a
    real change.
    """
    head = font['head']
    head.created = head.modified = timeTools.timestampNow()

    if path.is_file():
        previous = TTFont(path, recalcTimestamp=False)
        head.created = previous['head'].created
        head.modified = previous['head'].modified
        if compile_font(font) != compile_font(previous):
            head.modified = timeTools.timestampNow()

    font.save(path)


def fill_codepoint(codepoint: int) -> int:
    """Return the codepoint encoding the filled form of *codepoint*.

    See :data:`FILL_CODEPOINT_PLANE` for why the low word is mirrored instead of
    the whole codepoint being offset.
    """
    return FILL_CODEPOINT_PLANE + (codepoint & 0xFFFF)


def map_icon_codepoints(
    font: TTFont,
    ligatures: dict[str, str],
) -> tuple[dict[str, int], dict[int, str]]:
    """Assign a codepoint to both forms of every icon of *ligatures*, and return
    ({outlined name: codepoint}, {codepoint: glyph}).

    Outlined glyphs are left where Google encoded them in *font*, so that the
    mapping stays the upstream one and adding an icon does not renumber the
    others; the filled glyphs, which upstream never encodes, get the codepoint
    :func:`fill_codepoint` derives from their outlined counterpart.  An outlined
    glyph that upstream leaves unencoded is given a spare BMP PUA slot.

    Only the outlined codepoints are returned by name: the filled ones are a pure
    function of them, which is what lets the generated mapping list half as many
    and compute the rest (see :func:`write_python_icon_list`).

    Several names may share one glyph (``help`` / ``help_outline``,
    ``chevron_left`` / ``chevron_backward`` …); they share its codepoint too.
    """
    encoded = font.getBestCmap()
    glyph_codepoint = {}
    for codepoint, glyph in sorted(encoded.items()):
        glyph_codepoint.setdefault(glyph, codepoint)  # aliases: lowest wins
    spare = (cp for cp in range(PUA_START, PUA_END + 1) if cp not in encoded)

    codepoints, codepoint_to_glyph = {}, {}
    for name, glyph in sorted(ligatures.items()):
        if name.endswith(FILL_SUFFIX):
            continue  # encoded along with the outlined form it belongs to

        codepoint = glyph_codepoint.get(glyph)
        if codepoint is None:
            codepoint = next(spare, None)
            if codepoint is None:
                raise ValueError(f"No private-use codepoint left to encode {name!r}.")
            glyph_codepoint[glyph] = codepoint
        codepoints[name] = codepoint
        codepoint_to_glyph[codepoint] = glyph

        # The computed filled codepoint is only ever right if every icon has a
        # filled form to point at -- :func:`build_font` falls back on the
        # outlined glyph for the icons whose shape does not change with FILL.
        filled_name = name + FILL_SUFFIX
        filled_glyph = ligatures.get(filled_name)
        if filled_glyph is None:
            raise ValueError(f"{name!r} has no {filled_name!r} counterpart to encode.")
        filled_codepoint = fill_codepoint(codepoint)
        owner = codepoint_to_glyph.setdefault(filled_codepoint, filled_glyph)
        if owner != filled_glyph:
            raise ValueError(
                f"Cannot encode {filled_name!r} at U+{filled_codepoint:04X}: "
                f"the codepoint already maps to {owner!r}.",
            )

    return codepoints, codepoint_to_glyph


def add_cmap_entries(font: TTFont, codepoint_to_glyph: dict[int, str]) -> None:
    """Add *codepoint_to_glyph* to every Unicode cmap subtable of *font*.

    Format 4 subtables only get the BMP part, being unable to encode anything
    above U+FFFF, and a format 12 subtable is created from the widest existing
    mapping if the font has none: every fill codepoint needs one, sitting in
    Plane 16.
    """
    cmap = font['cmap']
    tables = [table for table in cmap.tables if table.isUnicode()]
    if not any(table.format == 12 for table in tables):
        table = CmapSubtable.newSubtable(12)
        table.platformID, table.platEncID, table.language = 3, 10, 0
        table.cmap = dict(max(tables, key=lambda t: len(t.cmap)).cmap)
        cmap.tables.append(table)
        tables.append(table)

    for table in tables:
        table.cmap.update(
            codepoint_to_glyph if table.format == 12
            else {cp: glyph for cp, glyph in codepoint_to_glyph.items() if cp <= 0xFFFF},
        )


def strip_icon_codepoints(font: TTFont, ligatures: dict[str, str]) -> None:
    """Drop from the cmap of *font* everything but the characters the icon names
    are spelled with.

    The icons of the web fonts are only ever reached through their ligature, so
    the codepoints Google encodes its glyphs at are dead weight — and an
    ambiguity, an icon having two ways in and only one of them going through the
    FILL axis.  The ASCII glyphs the ligature reads as input have to stay.
    """
    kept = {ord(char) for name in ligatures for char in name}
    for table in font['cmap'].tables:
        table.cmap = {cp: glyph for cp, glyph in table.cmap.items() if cp in kept}


def clone_font(font: TTFont) -> TTFont:
    """Round-trip *font* through memory so the backend font is independent."""
    data = BytesIO()
    font.save(data)
    return TTFont(
        BytesIO(data.getvalue()),
        recalcBBoxes=False,
        recalcTimestamp=False,
    )


def build_backend_font(
    merged: TTFont,
    style: str,
    codepoint_to_glyph: dict[int, str],
    filled_glyphs: dict[str, str],
) -> TTFont:
    """Clone *merged* into the WOFF the server renders with.

    Two consumers, two ways in.  wkhtmltopdf lays out the report HTML the same
    way a browser would, ligature and FILL axis included, but cannot read WOFF2,
    hence a WOFF; Pillow renders the mail icons with FreeType alone, no
    RAQM/HarfBuzz, so it needs the codepoints :func:`map_icon_codepoints` handed
    out — the ones :func:`strip_icon_codepoints` takes back out of the web fonts.

    Must be cloned before :func:`strip_font_metadata` drops the glyph names the
    cmap and the FILL axis are keyed by, hence the two of them being applied here
    a second time.
    """
    backend_font = clone_font(merged)
    add_cmap_entries(backend_font, codepoint_to_glyph)
    strip_font_metadata(backend_font, style)
    add_fill_axis(backend_font, filled_glyphs)
    backend_font.flavor = 'woff'
    return backend_font


def build_font(
    style: str,
    ms_dir: Path,
    wishlist: list[str],
    with_backend_font: bool = False,
):
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
    # Sorted, not in set order: fontext numbers the glyphs it keeps in the order
    # it is given them, so an unstable order would reshuffle the filled half of
    # the glyf table on every run and make two identical builds differ.
    icons_suffixed = sorted(i + FILL_SUFFIX for i in icons_with_fill)
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
    filled_glyphs = {}
    unresolved = []
    for icon, src in glyphs_map.items():
        if src not in outline_glyph:
            unresolved.append(icon)
            continue
        ligatures[icon] = outline_glyph[src]
        ligatures[icon + FILL_SUFFIX] = fill_glyph.get(src, outline_glyph[src])
        # Icons with no filled variant are left out, the axis being a no-op for
        # them.  A glyph shared by several names (`help` / `help_outline` …) is
        # listed once.
        if src in fill_glyph and fill_glyph[src] != outline_glyph[src]:
            filled_glyphs[outline_glyph[src]] = fill_glyph[src]

    unresolved += build_gsub(merged, ligatures)
    if unresolved:
        print(f"  {len(unresolved)} icons could not be encoded: {sorted(unresolved)}")  # noqa: T201

    # Both from the font as it stands, upstream cmap and glyph names included:
    # the backend font is the only one keeping either.
    codepoints = backend_font = None
    if with_backend_font:
        codepoints, codepoint_to_glyph = map_icon_codepoints(merged, ligatures)
        backend_font = build_backend_font(merged, style, codepoint_to_glyph, filled_glyphs)

    strip_icon_codepoints(merged, ligatures)
    strip_font_metadata(merged, style)
    # After the metadata strip, see :func:`add_fill_axis`.
    add_fill_axis(merged, filled_glyphs)
    icons = {name: {'has_fill': name in icons_with_fill} for name in wishlist if name in glyphs_map}

    print("  Saving fonts…")  # noqa: T201
    ms_dir.mkdir(parents=True, exist_ok=True)

    output_font_path = ms_dir / f'material_symbols_{style.lower()}_subset.woff2'
    merged.flavor = 'woff2'
    save_font(merged, output_font_path)

    backend_font_path = None
    if backend_font is not None:
        backend_font_path = ms_dir / BACKEND_FONT_FILE
        save_font(backend_font, backend_font_path)

    write_font_face_css(ms_dir, style.lower(), output_font_path.name, backend_font_path)

    return icons, output_font_path, backend_font_path, codepoints


def write_font_face_css(ms_dir, style_lower: str, font_file: str, backend_font_path) -> None:
    sources = f"    src: url('/web/static/src/libs/materialsymbols/{font_file}') format('woff2')"
    fallback = ""
    if backend_font_path is not None:
        fallback = (
            "    /* WOFF fallback for wkhtmltopdf, which cannot read WOFF2. Browsers\n"
            "       only download the first format they support, so it costs nothing. */\n"
        )
        sources += (
            ",\n"
            f"         url('/web/static/src/libs/materialsymbols/{backend_font_path.name}') format('woff')"
        )

    css = (
        "/* Generated by `odoo/addons/web/tooling/icons/generate_icons.py` — do not edit manually. */\n"
        "@font-face {\n"
        f"    font-family: 'Material Symbols {style_lower.capitalize()}';\n"
        "    font-style: normal;\n"
        "    font-weight: 400;\n"
        "    font-display: block;\n"
        "    /* This font is a subset of the Material Symbols icons */\n"
        f"{fallback}"
        f"{sources};\n"
        "}\n"
    )
    (ms_dir / f'material_symbols_{style_lower}.css').write_text(css, encoding='utf-8')


def write_python_icon_list(dst_path, icons: dict[str, dict], codepoints: dict[str, int]) -> None:
    """Write the icon metadata (``has_fill`` flag, search ``tags`` and cmap
    ``codepoint``) as a Python dict.

    The dict is imported server-side by the ``/html_editor/material_symbols_search``
    controller, so the (large) search tags never ship to the browser, and no file
    has to be read at runtime.  Only the outlined codepoints are listed; the
    filled ones are computed the way :func:`fill_codepoint` encodes them.
    """
    url = "https://fonts.google.com/metadata/icons?key=material_symbols&incomplete=true"
    with urllib.request.urlopen(url, timeout=30) as response:
        response_text = response.read().decode("utf-8")

    # The response is prefixed with an anti-JSON-hijacking guard.
    metadata = json.loads(response_text.removeprefix(")]}'"))
    for icon_data in metadata.get('icons', []):
        if icon_data['name'] in icons:
            icons[icon_data['name']]['tags'] = ' '.join(icon_data.get('tags', []))

    entries = '\n'.join(
        f"    {icon_name!r}: {{'has_fill': {icon['has_fill']}, "
        f"'codepoint': 0x{codepoints[icon_name]:04X}, 'tags': {icon.get('tags', '')!r}}},"
        for icon_name, icon in icons.items()
    )
    dst_path.write_text(
        "# Part of Odoo. See LICENSE file for full copyright and licensing details.\n"
        "\n"
        '"""Material Symbols icon metadata used by the icon picker.\n'
        "\n"
        "Generated by ``odoo/addons/web/tooling/icons/generate_icons.py`` -- do not edit\n"
        "manually.\n"
        "\n"
        "Maps each icon name to its ``has_fill`` flag and the space-separated ``tags``\n"
        "used to search it. The tags are only ever matched server-side (see the\n"
        "``/html_editor/material_symbols_search`` controller), so they never reach the browser.\n"
        '"""\n'
        "\n"
        f"MS_ICONS = {{\n{entries}\n}}\n",
        encoding='utf-8',
    )


def main() -> None:
    check_fontext()

    module_path = Path(__file__).resolve().parents[2]  # .../web/tooling/icons → .../web
    if not module_path.exists():
        sys.exit("Could not locate the 'web' module.")

    ms_dir = module_path / 'static' / 'src' / 'libs' / 'materialsymbols'
    wishlist = load_wishlist()

    # Only the outlined font is rendered server-side, so only it gets a backend
    # clone.
    icons, outline_path, backend_path, codepoints = build_font(
        "Outlined", ms_dir, wishlist, with_backend_font=True,
    )
    _, sharp_path, *_ = build_font("Sharp", ms_dir, wishlist)

    icon_list_path = module_path.parent / 'html_editor' / 'controllers' / 'ms_icons.py'
    write_python_icon_list(icon_list_path, icons, codepoints)

    n_filled = sum(1 for icon in icons.values() if icon['has_fill'])
    print(  # noqa: T201
        f"\n✓  Generated fonts with {len(icons)} icons ({n_filled} with filled variant)\n"
        f"   outlined web     → {outline_path}  ({outline_path.stat().st_size // 1000} kb)\n"
        f"   sharp web        → {sharp_path}  ({sharp_path.stat().st_size // 1000} kb)\n"
        f"   outlined backend → {backend_path}  ({backend_path.stat().st_size // 1000} kb)\n"
        f"   Python metadata  → {icon_list_path}  ({len(codepoints)} codepoints)\n",
    )


if __name__ == "__main__":
    main()
