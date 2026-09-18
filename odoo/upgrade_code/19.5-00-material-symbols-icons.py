"""Migrate FontAwesome / odoo-ui-icons markup to the Material Symbols system.

Icons used to be rendered by a CSS class (``<i class="fa fa-user"/>``,
``<i class="oi oi-archive"/>``). They are now rendered by the ``oi`` class plus a
``data-icon`` attribute holding the Material Symbols ligature
(``<i class="oi" data-icon="person"/>``), and the FontAwesome stylesheet is gone.

This script rewrites the patterns that carry an icon name:

- ``class="fa fa-user"`` / ``class="oi oi-archive"`` → ``class="oi" data-icon="..."``
- ``t-att-class`` / ``t-attf-class`` expressions made of icon literals →
  ``t-att-data-icon`` / ``t-attf-data-icon``
- ``icon="fa-user"`` view attributes → ``icon="person" icon_class="oi-filled"``
- ``'icon': 'fa fa-user'`` dict entries (views, Python, JS)
- standalone icon strings in JS (``return "fa fa-phone"``, ``badgeIcon: "fa-x"``)
- ``.fa-user`` CSS/test selectors → ``[data-icon='person']``
- the ``icon_class`` OWL prop, renamed to ``iconClass`` (the view *arch*
  attribute keeps its snake_case spelling)

``fa-fw``, ``fa-spin``, ``fa-2x``… modifiers become their ``oi-`` counterparts,
and the ones that carry nothing over (``fa-1x``, ``fa-inverse``) are dropped.
Icons whose FontAwesome variant was filled get the ``oi-filled`` modifier.

This is a best-effort rewrite: dynamically built class names, icons stored in
data and unusual markup are not covered and need a manual pass.
"""

from __future__ import annotations

import re
import typing

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager


# ---------------------------------------------------------------------------
# MAPPINGS
# ---------------------------------------------------------------------------

def _parse_icon_map(raw: str) -> dict[str, tuple[str, bool]]:
    """Parse the ``name>icon[!]`` table into ``{name: (icon, filled)}``."""
    result = {}
    for token in raw.split():
        name, _, icon = token.partition('>')
        result[name] = (icon.rstrip('!'), icon.endswith('!'))
    return result


# fa-* modifier classes → the oi-* utilities that icons.scss actually defines.
# `fa-xs` has no counterpart there, so it is left in place rather than renamed
# to a class that would not exist.
FA_UTIL_TO_OI = {
    'fw': 'oi-fw', 'spin': 'oi-spin', 'pulse': 'oi-pulse', 'lg': 'oi-lg',
    'sm': 'oi-sm', 'stack': 'oi-stack',
    'stack-1x': 'oi-stack-1x', 'stack-2x': 'oi-stack-2x',
    'rotate-90': 'oi-rotate-90', 'rotate-180': 'oi-rotate-180',
    'rotate-270': 'oi-rotate-270',
    'flip-horizontal': 'oi-flip-horizontal', 'flip-vertical': 'oi-flip-vertical',
    **{f'{n}x': f'oi-{n}x' for n in range(2, 11)},
}

# oi-* classes that are modifiers, not icon names
OI_UTIL_CLASSES = frozenset({'oi-filled', 'oi-outlined', *FA_UTIL_TO_OI.values()})

# fa-* modifiers with nothing to carry over: `fa-1x` is the default size (and
# FontAwesome 4 never defined it), `fa-inverse` has no equivalent.
FA_NOOP_MODIFIERS = frozenset({'1x', 'inverse'})


def _ambiguous_filled_icons() -> frozenset[str]:
    """Icons reachable from both a filled and a non-filled fa-* class.

    ``fa-star`` gives ``(star, filled)`` and ``fa-star-o`` gives ``(star, not
    filled)``: a bare ``[data-icon='star']`` selector cannot tell them apart, so
    CSS rewrites must append ``.oi-filled`` / ``:not(.oi-filled)``. Icons that
    are always (or never) filled stay ambiguity-free so we don't emit noise.
    """
    flags: dict[str, set[bool]] = {}
    for icon, filled in FA_TO_MATERIAL.values():
        flags.setdefault(icon, set()).add(filled)
    return frozenset(icon for icon, f in flags.items() if f == {True, False})


def _filled_suffix(fa_name: str) -> str:
    icon, filled = FA_TO_MATERIAL[fa_name]
    if icon in AMBIGUOUS_FILLED_ICONS:
        return '.oi-filled' if filled else ':not(.oi-filled)'
    return ''


# ---------------------------------------------------------------------------
# CLASS LISTS
# ---------------------------------------------------------------------------

def _split_fa_classes(classes: list[str]) -> tuple[str | None, list[str], list[str]]:
    """Split into (icon name, fa modifier names, classes to keep as-is)."""
    icon, modifiers, others = None, [], []
    for cls in classes:
        if cls == 'fa':
            continue
        if not cls.startswith('fa-'):
            others.append(cls)
            continue
        name = cls[3:]
        if name in FA_TO_MATERIAL and icon is None:
            icon = name
        elif name in FA_UTIL_TO_OI:
            modifiers.append(name)
        elif name not in FA_NOOP_MODIFIERS:
            others.append(cls)
    return icon, modifiers, others


def _split_oi_classes(classes: list[str]) -> tuple[str | None, list[str], list[str]]:
    """Split into (icon name, oi modifier classes, classes to keep as-is)."""
    icon, modifiers, others = None, [], []
    for cls in classes:
        if cls == 'oi':
            continue
        if not cls.startswith('oi-'):
            others.append(cls)
            continue
        if cls[3:] in OI_TO_MATERIAL and icon is None:
            icon = cls[3:]
        elif cls in OI_UTIL_CLASSES:
            modifiers.append(cls)
        else:
            others.append(cls)
    return icon, modifiers, others


def _build_classes(modifiers: list[str], others: list[str], filled: bool) -> str:
    classes = ['oi']
    for modifier in modifiers:
        modifier = FA_UTIL_TO_OI.get(modifier, modifier)
        if modifier not in classes:
            classes.append(modifier)
    if filled and 'oi-filled' not in classes:
        classes.append('oi-filled')
    return ' '.join(classes + others)


def _class_to_icon(class_value: str) -> tuple[str, str] | None:
    """Return (new class value, data-icon value) for an icon class string."""
    classes = class_value.split()
    if 'fa' in classes:
        name, modifiers, others = _split_fa_classes(classes)
        if name is not None:
            icon, filled = FA_TO_MATERIAL[name]
            return _build_classes(modifiers, others, filled), icon
    if 'oi' in classes:
        name, modifiers, others = _split_oi_classes(classes)
        if name is not None:
            icon, filled = OI_TO_MATERIAL[name]
            return _build_classes(modifiers, others, filled), icon
    return None


def _fa_classes_to_oi(class_value: str) -> str | None:
    """Convert a fa-* class string to oi-* modifiers, dropping the icon class.

    Used when the icon itself comes from a dynamic attribute rather than from
    the static ``class``.
    """
    classes = class_value.split()
    if 'fa' not in classes:
        return None
    _icon, modifiers, others = _split_fa_classes(classes)
    return _build_classes(modifiers, others, False)


def _icon_and_fill(class_value: str) -> tuple[str, bool] | tuple[None, None]:
    """Return (icon, filled) for the first icon class of a class string."""
    for cls in class_value.split():
        if cls.startswith('fa-') and cls[3:] in FA_TO_MATERIAL:
            return FA_TO_MATERIAL[cls[3:]]
        if cls.startswith('oi-') and cls[3:] in OI_TO_MATERIAL:
            return OI_TO_MATERIAL[cls[3:]]
    return None, None


def _icon_literal(class_value: str) -> str | None:
    return _icon_and_fill(class_value)[0]


# ---------------------------------------------------------------------------
# XML / HTML TAGS
# ---------------------------------------------------------------------------

# A whole opening tag, quoted attribute values included so that a '>' inside an
# expression (t-on-click="() => ...") does not end the match early.
TAG_RE = re.compile(r"""<[A-Za-z][\w.:-]*(?:[^>"']|"[^"]*"|'[^']*')*>""", re.DOTALL)
CLASS_ATTR_RE = re.compile(r"""(?<![-\w])class=(["'])(.*?)\1""", re.DOTALL)
T_ATT_CLASS_RE = re.compile(r"""\bt-att-class=(["'])(.*?)\1""", re.DOTALL)
T_ATTF_CLASS_RE = re.compile(r"""\bt-attf-class=(["'])(.*?)\1""", re.DOTALL)
DATA_ICON_RE = re.compile(r'\b(?:data-icon|t-att-data-icon|t-attf-data-icon)\s*=')
QUOTED_RE = re.compile(r"'([^']*)'")
# fa-fw, fa-2x, fa-1x… left over on an element that already renders through oi
FA_MODIFIER_RE = re.compile(
    r'(?<![\w-])fa-(%s)(?![\w-])'
    % '|'.join(sorted(
        map(re.escape, (*FA_UTIL_TO_OI, *FA_NOOP_MODIFIERS)), key=len, reverse=True,
    )),
)
OI_SIGNAL_RE = re.compile(r'(?<![\w-])oi(?:-\w+)?(?![\w-])')


def _append_attribute(tag: str, attribute: str) -> str:
    if tag.endswith('/>'):
        return f'{tag[:-2]} {attribute}/>'
    return f'{tag[:-1]} {attribute}>'


def _rewrite_class_attr(tag: str) -> str:
    if DATA_ICON_RE.search(tag):
        return tag
    match = CLASS_ATTR_RE.search(tag)
    if not match or '{' in match.group(2):
        return tag
    result = _class_to_icon(match.group(2))
    if not result:
        return tag
    classes, icon = result
    quote = match.group(1)
    attributes = f'class={quote}{classes}{quote} data-icon={quote}{icon}{quote}'
    return tag[:match.start()] + attributes + tag[match.end():]


def _rewrite_t_att_class(tag: str) -> str:
    """``t-att-class="x ? 'fa-eye' : 'fa-eye-slash'"`` → ``t-att-data-icon=...``

    Only when every quoted literal of the expression is an icon class.
    """
    if re.search(r'\bt-att-data-icon\s*=', tag):
        return tag
    match = T_ATT_CLASS_RE.search(tag)
    if not match:
        return tag
    literals = QUOTED_RE.findall(match.group(2))
    icons = {literal: _icon_literal(literal) for literal in literals}
    if not literals or None in icons.values():
        return tag

    value = QUOTED_RE.sub(lambda m: f"'{icons[m.group(1)]}'", match.group(2))
    quote = match.group(1)
    tag = tag[:match.start()] + f't-att-data-icon={quote}{value}{quote}' + tag[match.end():]

    match = CLASS_ATTR_RE.search(tag)
    if match and '{' not in match.group(2):
        classes = _fa_classes_to_oi(match.group(2))
        if classes is not None:
            quote = match.group(1)
            tag = tag[:match.start()] + f'class={quote}{classes}{quote}' + tag[match.end():]
    return tag


def _rewrite_t_attf_class(tag: str) -> str:
    """Convert the static part of a ``t-attf-class`` and extract its icon.

    ``"fa fa-fw #{x ? 'fa-lock' : 'fa-unlock'}"`` becomes
    ``"oi oi-fw #{x ? '' : ''}"`` plus ``t-attf-data-icon="#{x ? 'lock' : 'lock_open'}"``.
    """
    if re.search(r'\bt-attf-data-icon\s*=', tag):
        return tag
    match = T_ATTF_CLASS_RE.search(tag)
    if not match:
        return tag
    quote, value = match.group(1), match.group(2)

    blocks = list(re.finditer(r'(#\{.*?\}|\{\{.*?\}\})', value, re.DOTALL))
    static_end = blocks[0].start() if blocks else len(value)
    static, dynamic = value[:static_end], value[static_end:]

    static_icon = None
    if {'fa', 'oi'} & set(static.split()):
        trailing = static[len(static.rstrip()):]
        result = _class_to_icon(static.strip())
        if result:
            static, static_icon = result[0] + trailing, result[1]
        else:
            classes = _fa_classes_to_oi(static.strip())
            if classes is not None:
                static = classes + trailing

    icon_parts, class_parts = [], []
    for block in blocks:
        content = block.group(0)
        opening, closing = ('#{', '}') if content.startswith('#{') else ('{{', '}}')
        inner = content[len(opening):-len(closing)]
        icons, residuals = {}, {}
        for literal in QUOTED_RE.findall(inner):
            icon = _icon_literal(literal)
            if icon is None:
                icons = None
                break
            icons[literal] = icon
            residuals[literal] = ' '.join(
                cls for cls in literal.split()
                if cls not in ('fa', 'oi') and _icon_literal(cls) is None
            )
        if not icons:
            icon_parts.append(None)
            class_parts.append(content)
            continue
        icon_inner = QUOTED_RE.sub(lambda m: f"'{icons[m.group(1)]}'", inner)
        icon_parts.append(f'{opening}{icon_inner}{closing}')
        class_inner = QUOTED_RE.sub(lambda m: f"'{residuals[m.group(1)]}'", inner)
        class_parts.append(f'{opening}{class_inner}{closing}')

    if blocks and all(part is not None for part in icon_parts):
        rewritten, end = static, static_end
        for block, part in zip(blocks, class_parts):
            rewritten += value[end:block.start()] + part
            end = block.end()
        rewritten += value[end:]
        tag = tag[:match.start()] + f't-attf-class={quote}{rewritten}{quote}' + tag[match.end():]
        return _append_attribute(tag, f'''t-attf-data-icon="{' '.join(icon_parts)}"''')

    if static + dynamic != value:
        tag = tag[:match.start()] + f't-attf-class={quote}{static}{dynamic}{quote}' + tag[match.end():]

    match = CLASS_ATTR_RE.search(tag)
    if match and '{' not in match.group(2):
        classes = _fa_classes_to_oi(match.group(2))
        if classes is not None:
            quote = match.group(1)
            tag = tag[:match.start()] + f'class={quote}{classes}{quote}' + tag[match.end():]

    if static_icon and not DATA_ICON_RE.search(tag):
        tag = _append_attribute(tag, f'data-icon="{static_icon}"')
    return tag


def _normalize_modifiers(tag: str) -> str:
    """Turn leftover fa-* modifiers into oi-* ones on oi-rendered elements.

    An element deliberately kept on FontAwesome carries no oi signal, so it is
    left alone.
    """
    if not (DATA_ICON_RE.search(tag) or OI_SIGNAL_RE.search(tag)):
        return tag
    match = CLASS_ATTR_RE.search(tag)
    original = match.group(2).split() if match and '{' not in match.group(2) else None

    # a no-op modifier substitutes to nothing, hence the leftover blanks the
    # class attribute is rebuilt from tokens below
    tag = FA_MODIFIER_RE.sub(lambda m: FA_UTIL_TO_OI.get(m.group(1), ''), tag)

    match = CLASS_ATTR_RE.search(tag)
    if original is None or not match:
        return tag
    classes = match.group(2).split()
    if 'fa' in classes and not any(cls.startswith('fa-') for cls in classes):
        classes = ['oi' if cls == 'fa' else cls for cls in classes]
    deduped = []
    for cls in classes:
        if cls not in deduped or cls not in OI_UTIL_CLASSES:
            deduped.append(cls)
    if deduped == original:
        return tag
    quote = match.group(1)
    return tag[:match.start()] + f"class={quote}{' '.join(deduped)}{quote}" + tag[match.end():]


def _rewrite_tags(content: str) -> str:
    def rewrite(match: re.Match) -> str:
        tag = match.group(0)
        tag = _rewrite_class_attr(tag)
        tag = _rewrite_t_att_class(tag)
        tag = _rewrite_t_attf_class(tag)
        return _normalize_modifiers(tag)
    return TAG_RE.sub(rewrite, content)


# ---------------------------------------------------------------------------
# icon= ATTRIBUTES (buttons, stat buttons, fields, OWL props)
# ---------------------------------------------------------------------------

ICON_ATTR_RE = re.compile(
    r"""(\sicon=\s*)(["'])((?:'[^']*'|[\w\s-]+))\2((?:[^>"']*(?!icon))*)""",
    re.DOTALL,
)


def _icon_attr_sub(match: re.Match) -> str:
    prefix, quote, value, rest = match.groups()
    # OWL props hold a JS expression: icon="'fa-user'"
    is_prop = value.startswith("'") and value.endswith("'")
    classes = (value[1:-1] if is_prop else value).split()
    if not classes:
        return match.group(0)

    icon, filled, extras = None, False, []
    for cls in classes:
        if cls in ('fa', 'oi'):
            continue
        if cls.startswith('fa-') and cls[3:] in FA_TO_MATERIAL:
            icon, filled = FA_TO_MATERIAL[cls[3:]]
        elif cls.startswith('oi-') and cls[3:] in OI_TO_MATERIAL:
            icon, filled = OI_TO_MATERIAL[cls[3:]]
        elif cls.startswith('fa-') and cls[3:] in FA_UTIL_TO_OI:
            extras.append(FA_UTIL_TO_OI[cls[3:]])
        elif not cls.startswith('fa-'):
            extras.append(cls)
    if icon is None:
        return match.group(0)
    if filled:
        extras.insert(0, 'oi-filled')

    value = f"'{icon}'" if is_prop else icon
    result = f'{prefix}{quote}{value}{quote}'
    if extras and not re.search(r'\b(?:icon_class|iconClass)\s*=', rest[:160]):
        name = 'iconClass' if is_prop else 'icon_class'
        classes = ' '.join(extras)
        result += f' {name}="\'{classes}\'"' if is_prop else f' {name}="{classes}"'
    return result + rest


# ``'icon': 'fa fa-user'`` dict entries, in view attributes, Python and JS. The
# key of the older ``'iconClass': 'fa-user'`` spelling held the icon itself.
DICT_ICON_RE = re.compile(
    r"""(?<![\w-])(?P<kq>['"]?)(?:icon|iconClass)(?P=kq)\s*:\s*"""
    r"""(?P<q>['"])(?P<value>(?:fa|oi)[\w\s-]*)(?P=q)""",
)


def _dict_icon_sub(match: re.Match, class_key: str | None) -> str:
    kq, quote = match.group('kq'), match.group('q')
    icon, filled = _icon_and_fill(match.group('value'))
    if icon is None:
        return match.group(0)
    result = f'{kq}icon{kq}: {quote}{icon}{quote}'
    if filled and class_key:
        result += f', {kq}{class_key}{kq}: {quote}oi-filled{quote}'
    return result


# ---------------------------------------------------------------------------
# CSS SELECTORS (stylesheets, but also test helpers and querySelector calls)
# ---------------------------------------------------------------------------

SELECTOR_FA_RE = re.compile(r'(?:\.fa)?\.fa-([\w-]+)(?![\w-])')
SELECTOR_OI_RE = re.compile(r'\.oi-([\w-]+)(?![\w-])')


def _selector_fa_sub(match: re.Match, quote: str = "'") -> str:
    name = match.group(1)
    if name in FA_TO_MATERIAL:
        return f'[data-icon={quote}{FA_TO_MATERIAL[name][0]}{quote}]{_filled_suffix(name)}'
    if name in FA_UTIL_TO_OI:
        return f'.{FA_UTIL_TO_OI[name]}'
    return match.group(0)


def _selector_oi_sub(match: re.Match, quote: str = "'") -> str:
    name = match.group(1)
    if name in OI_TO_MATERIAL:
        return f'[data-icon={quote}{OI_TO_MATERIAL[name][0]}{quote}]'
    return match.group(0)


def _rewrite_selectors(content: str, quote: str = "'") -> str:
    content = SELECTOR_FA_RE.sub(lambda m: _selector_fa_sub(m, quote), content)
    return SELECTOR_OI_RE.sub(lambda m: _selector_oi_sub(m, quote), content)


# ---------------------------------------------------------------------------
# JS
# ---------------------------------------------------------------------------

JS_ICON_FIELD_RE = re.compile(
    r"""(\b(?:icon|prefixIcon|titleIcon|done_icon)\b["']?\s*[:=]\s*)(["'])((?:fa|oi)[\w\s-]*)\2""",
)
JS_STRING_RE = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'')
# class manipulation needs the literal class name, not an icon name
CLASS_MANIP_RE = re.compile(r'\b(?:classList|className)\b|\w+Class\(')
TO_HAVE_CLASS_RE = re.compile(r'\btoHaveClass\((["\'])((?:fa )?fa-[\w-]+)\1\)')


def _js_icon_field_sub(match: re.Match) -> str:
    prefix, quote, value = match.groups()
    icon = _icon_literal(value)
    return f'{prefix}{quote}{icon}{quote}' if icon else match.group(0)


def _pure_icon_string(value: str) -> str | None:
    """Return the icon when ``value`` is made of icon classes only.

    Strings carrying unrelated classes (``"fa fa-user text-danger"``) are left
    alone: they are class lists, not icon names.
    """
    icon = None
    for cls in value.split():
        if cls in ('fa', 'oi') or cls in OI_UTIL_CLASSES:
            continue
        if cls.startswith('fa-'):
            name = cls[3:]
            if name in FA_UTIL_TO_OI or name in FA_NOOP_MODIFIERS:
                continue
            if name not in FA_TO_MATERIAL or icon:
                return None
            icon = FA_TO_MATERIAL[name][0]
        elif cls.startswith('oi-'):
            if cls[3:] not in OI_TO_MATERIAL or icon:
                return None
            icon = OI_TO_MATERIAL[cls[3:]][0]
        else:
            return None
    return icon


def _rewrite_icon_strings(content: str) -> str:
    def rewrite(match: re.Match) -> str:
        # The class manipulation may open several lines above the literal, as in
        # a multi-line `classList.add(...)`, so look back to the start of the
        # statement and not merely to the start of the line.
        window = max(0, match.start() - 300)  # bounded, to stay linear
        statement_start = max(
            content.rfind(character, window, match.start()) for character in ';{}'
        ) + 1
        line_end = content.find('\n', match.start())
        around = content[max(statement_start, window):line_end if line_end != -1 else None]
        if CLASS_MANIP_RE.search(around):
            return match.group(0)
        # An object key is a class name used as a toggle, not an icon value:
        #     { "fa-arrows-alt": !fullscreen, "fa-compress": fullscreen }
        # Walk over the surrounding blanks by index: slicing the content here
        # copies the whole file on every literal, which is quadratic.
        start = match.start() - 1
        while start >= 0 and content[start].isspace():
            start -= 1
        end = match.end()
        while end < len(content) and content[end].isspace():
            end += 1
        before = content[start] if start >= 0 else ''
        after = content[end] if end < len(content) else ''
        if after == ':' and before in '{,(':
            return match.group(0)
        icon = _pure_icon_string(match.group(0)[1:-1])
        return f'{match.group(0)[0]}{icon}{match.group(0)[0]}' if icon else match.group(0)
    return JS_STRING_RE.sub(rewrite, content)


def _to_have_class_sub(match: re.Match) -> str:
    name = match.group(2).split()[-1][3:]
    if name not in FA_TO_MATERIAL:
        return match.group(0)
    return f'toHaveAttribute("data-icon", "{FA_TO_MATERIAL[name][0]}")'


def _rewrite_selectors_in_js(content: str) -> str:
    """Rewrite selectors, quoting ``data-icon`` values so JS strings stay valid.

    ``[data-icon='edit']`` inside a single-quoted JS string would break it, so
    each string literal is rewritten with the opposite quote.
    """
    result, position = [], 0
    for match in JS_STRING_RE.finditer(content):
        result.append(_rewrite_selectors(content[position:match.start()]))
        quote = '"' if match.group(0)[0] == "'" else "'"
        result.append(_rewrite_selectors(match.group(0), quote))
        position = match.end()
    result.append(_rewrite_selectors(content[position:]))
    return ''.join(result)


# ---------------------------------------------------------------------------
# icon_class → iconClass (OWL prop; the view arch attribute is left untouched)
# ---------------------------------------------------------------------------

# a component tag: its attributes are OWL props
COMPONENT_TAG_RE = re.compile(r"""<[A-Z][\w.]*(?:[^>"']|"[^"]*"|'[^']*')*>""", re.DOTALL)
ICON_CLASS_RE = re.compile(r'(?<![\w])icon_class(?![\w])')
PROPS_ICON_CLASS_RE = re.compile(r'(?<=\bprops\.)icon_class(?![\w])')


def _rename_icon_class(content: str) -> str:
    """Rename the prop where it is unambiguously one: passed to a component, or
    read off ``props``.

    Any other ``icon_class`` is left alone, because the name is also the arch
    attribute and stays snake_case there. A plain ``icon_class`` key carries no
    signal of which one it is — ``options.icon_class`` reads the arch of a field
    widget, while an object holding ``icon_class`` may be read back from a
    template by the same name. Renaming one side of either pair silently breaks
    it, so both are left for a manual pass.
    """
    content = COMPONENT_TAG_RE.sub(lambda m: ICON_CLASS_RE.sub('iconClass', m.group(0)), content)
    return PROPS_ICON_CLASS_RE.sub('iconClass', content)


# ---------------------------------------------------------------------------
# PER FILE TYPE
# ---------------------------------------------------------------------------

# icons of the website rating snippet live in their own attribute
RATING_ICON_RE = re.compile(
    r'(<[^>]*\bclass="[^"]*s_rating[^"]*"[^>]*)\bdata-icon="fa-([a-z][a-z0-9-]*)"',
)


def transform_xml(content: str) -> str:
    content = _rewrite_tags(content)
    content = ICON_ATTR_RE.sub(_icon_attr_sub, content)
    content = DICT_ICON_RE.sub(lambda m: _dict_icon_sub(m, 'icon_class'), content)
    content = RATING_ICON_RE.sub(lambda m: f'{m.group(1)}data-rating-icon="{m.group(2)}"', content)
    return _rename_icon_class(content)


def transform_js(content: str, is_test: bool) -> str:
    content = _rewrite_tags(content)  # markup in template literals
    content = ICON_ATTR_RE.sub(_icon_attr_sub, content)
    # no iconClass is added here: an unexpected key would break OWL prop validation
    content = DICT_ICON_RE.sub(lambda m: _dict_icon_sub(m, None), content)
    content = JS_ICON_FIELD_RE.sub(_js_icon_field_sub, content)
    content = _rewrite_selectors_in_js(content)
    if is_test:
        # a test asserts on the rendered markup, not on an icon name
        content = TO_HAVE_CLASS_RE.sub(_to_have_class_sub, content)
    else:
        content = _rewrite_icon_strings(content)
    return _rename_icon_class(content)


def transform_python(content: str) -> str:
    content = _rewrite_tags(content)  # markup in Markup() literals
    return DICT_ICON_RE.sub(lambda m: _dict_icon_sub(m, 'iconClass'), content)


def transform_scss(content: str) -> str:
    content = re.sub(r'''(?<!['"])\.fa(?![\w-])''', '.oi', content)
    return _rewrite_selectors(content)


# `web` defines the icon system itself: its remaining fa-* references describe
# the migration, they are not markup to migrate.
SKIPPED_ADDONS = frozenset({'web'})
# vendored code, which follows its own upstream
SKIPPED_DIRECTORIES = frozenset({'lib', 'node_modules', 'o_spreadsheet'})


def upgrade(file_manager: FileManager):
    files = [
        file for file in file_manager
        if file.path.suffix in ('.xml', '.js', '.py', '.scss', '.css')
        if file.addon.name not in SKIPPED_ADDONS
        if SKIPPED_DIRECTORIES.isdisjoint(file.path.parts)
    ]
    for fileno, file in enumerate(files, start=1):
        suffix = file.path.suffix
        if suffix == '.xml':
            file.content = transform_xml(file.content)
        elif suffix == '.js':
            is_test = '.test.' in file.path.name or 'tests' in file.path.parts
            file.content = transform_js(file.content, is_test)
        elif suffix == '.py':
            file.content = transform_python(file.content)
        else:
            file.content = transform_scss(file.content)
        file_manager.print_progress(fileno, len(files))


# ---------------------------------------------------------------------------
# ICON TABLES
#
# ``legacy-name>material-icon`` pairs, ``!`` marking the filled variant. Icons
# prefixed with ``oi_`` are served by the odoo icon font instead of Material
# Symbols. Extracted from the SCSS maps that used to live in
# web/static/src/webclient/icons_mappings/ (dropped in 19.5).
# ---------------------------------------------------------------------------

FA_TO_MATERIAL = _parse_icon_map("""
500px>oi_500px address-book>contact_page! address-book-o>contact_page address-card>contact_mail!
vcard>contact_mail! address-card-o>contact_mail vcard-o>contact_mail adjust>contrast adn>oi_adn
align-center>format_align_center align-justify>format_align_justify align-left>format_align_left
align-right>format_align_right amazon>oi_amazon ambulance>emergency
american-sign-language-interpreting>sign_language asl-interpreting>sign_language anchor>anchor
android>oi_android angellist>oi_angellist angle-double-down>keyboard_double_arrow_down
angle-double-left>keyboard_double_arrow_left angle-double-right>keyboard_double_arrow_right
angle-double-up>keyboard_double_arrow_up angle-down>keyboard_arrow_down
angle-left>keyboard_arrow_left angle-right>keyboard_arrow_right angle-up>keyboard_arrow_up
apple>oi_apple archive>archive area-chart>area_chart arrow-circle-down>arrow_circle_down!
arrow-circle-left>arrow_circle_left! arrow-circle-o-down>arrow_circle_down
arrow-circle-o-left>arrow_circle_left arrow-circle-o-right>arrow_circle_right
arrow-circle-o-up>arrow_circle_up arrow-circle-right>arrow_circle_right!
arrow-circle-up>arrow_circle_up! arrow-down>arrow_downward arrow-left>arrow_back
arrow-right>arrow_forward arrow-up>arrow_upward arrows>open_with arrows-alt>open_with
arrows-h>swap_horiz arrows-v>swap_vert assistive-listening-systems>hearing asterisk>emergency
at>alternate_email audio-description>audio_description automobile>directions_car
car>directions_car backward>fast_rewind balance-scale>balance ban>block bandcamp>oi_bandcamp
bank>account_balance institution>account_balance university>account_balance bar-chart>bar_chart
bar-chart-o>bar_chart barcode>barcode bars>menu navicon>menu reorder>menu bath>bathtub
bathtub>bathtub s15>bathtub battery>battery_full battery-4>battery_full
battery-full>battery_full battery-0>battery_0_bar battery-empty>battery_0_bar
battery-1>battery_2_bar battery-quarter>battery_2_bar battery-2>battery_3_bar
battery-half>battery_3_bar battery-3>battery_5_bar battery-three-quarters>battery_5_bar bed>bed
hotel>bed beer>sports_bar behance>oi_behance behance-square>oi_behance-square
bell>notifications! bell-o>notifications bell-slash>notifications_off!
bell-slash-o>notifications_off bicycle>directions_bike binoculars>oi_binoculars
birthday-cake>cake bitbucket>oi_bitbucket bitbucket-square>oi_bitbucket-square
bitcoin>currency_bitcoin btc>currency_bitcoin black-tie>oi_black-tie blind>blind
bluetooth>bluetooth bluetooth-b>bluetooth bold>format_bold bolt>flash_on flash>flash_on
bomb>oi_bomb book>book bookmark>bookmark! bookmark-o>bookmark braille>grain briefcase>work
bug>bug_report building>business building-o>business bullhorn>campaign bullseye>crisis_alert
bus>directions_bus buysellads>oi_buysellads cab>local_taxi taxi>local_taxi calculator>calculate
calendar>calendar_today! calendar-check-o>event_available calendar-minus-o>event_busy
calendar-o>calendar_today calendar-plus-o>calendar_add_on calendar-times-o>event_busy
camera>photo_camera camera-retro>photo_camera caret-down>arrow_drop_down caret-left>arrow_left
caret-right>arrow_right caret-square-o-down>arrow_drop_down_circle
toggle-down>arrow_drop_down_circle caret-square-o-left>arrow_circle_left
toggle-left>arrow_circle_left caret-square-o-right>arrow_circle_right
toggle-right>arrow_circle_right caret-square-o-up>arrow_circle_up toggle-up>arrow_circle_up
caret-up>arrow_drop_up cart-arrow-down>shopping_cart_checkout cart-plus>add_shopping_cart
cc>closed_caption cc-amex>oi_cc-amex cc-diners-club>oi_cc-diners-club cc-discover>oi_cc-discover
cc-jcb>oi_cc-jcb cc-mastercard>oi_cc-mastercard cc-paypal>oi_cc-paypal cc-stripe>oi_cc-stripe
cc-visa>oi_cc-visa certificate>verified chain>link link>link chain-broken>link_off
unlink>link_off check>check check-circle>check_circle! check-circle-o>check_circle
check-square>check_box! check-square-o>check_box chevron-circle-down>expand_circle_down!
chevron-circle-left>arrow_circle_left! chevron-circle-right>arrow_circle_right!
chevron-circle-up>expand_circle_up! chevron-down>expand_more chevron-left>chevron_left
chevron-right>chevron_right chevron-up>expand_less child>child_care chrome>oi_chrome
circle>circle! circle-o>circle circle-o-notch>autorenew circle-thin>radio_button_unchecked
clipboard>assignment clock-o>schedule clone>content_copy close>close remove>close times>close
cloud>cloud cloud-download>cloud_download cloud-upload>cloud_upload cny>currency_yen
jpy>currency_yen rmb>currency_yen yen>currency_yen code>code code-fork>fork_right
codepen>oi_codepen codiepie>oi_codiepie coffee>coffee cog>settings! gear>settings!
cogs>settings_applications gears>settings_applications columns>view_column comment>chat_bubble!
comment-o>chat_bubble commenting>mode_comment! commenting-o>mode_comment comments>forum!
comments-o>forum compass>explore compress>close_fullscreen connectdevelop>oi_connectdevelop
contao>oi_contao copy>content_copy files-o>content_copy copyright>copyright
creative-commons>oi_creative-commons credit-card>credit_card credit-card-alt>credit_card
crop>crop crosshairs>my_location css3>oi_css3 cube>deployed_code cubes>inventory_2
cut>content_cut scissors>content_cut cutlery>restaurant dashboard>speed tachometer>speed
dashcube>oi_dashcube database>database deaf>hearing_disabled deafness>hearing_disabled
hard-of-hearing>hearing_disabled dedent>format_indent_decrease outdent>format_indent_decrease
delicious>oi_delicious desktop>desktop_windows deviantart>oi_deviantart diamond>diamond
digg>oi_digg dollar>attach_money usd>attach_money dot-circle-o>radio_button_checked
download>download dribbble>oi_dribbble drivers-license>badge! id-card>badge!
drivers-license-o>badge id-card-o>badge dropbox>oi_dropbox drupal>oi_drupal edge>oi_edge
edit>edit! eercast>oi_eercast eject>eject ellipsis-h>more_horiz ellipsis-v>more_vert
empire>oi_empire ge>oi_empire envelope>mail! envelope-o>mail envelope-open>drafts!
envelope-open-o>drafts envelope-square>mail! envira>oi_envira eraser>ink_eraser etsy>oi_etsy
eur>euro euro>euro exchange>swap_horiz exclamation>priority_high exclamation-circle>error!
exclamation-triangle>warning warning>warning expand>expand_content expeditedssl>oi_expeditedssl
external-link>open_in_new external-link-square>open_in_new eye>visibility
eye-slash>visibility_off eyedropper>colorize fa>oi_font-awesome font-awesome>oi_font-awesome
facebook>oi_facebook facebook-f>oi_facebook facebook-official>oi_facebook-official
facebook-square>oi_facebook-square fast-backward>fast_rewind fast-forward>fast_forward fax>fax
feed>rss_feed rss>rss_feed female>female fighter-jet>flight file>description!
file-archive-o>folder_zip file-zip-o>folder_zip file-audio-o>audio_file file-sound-o>audio_file
file-code-o>code file-excel-o>table_chart file-image-o>image file-photo-o>image
file-picture-o>image file-movie-o>video_file file-video-o>video_file file-o>description
file-pdf-o>picture_as_pdf file-powerpoint-o>slideshow file-text>article! file-text-o>article
file-word-o>description film>movie filter>filter_alt! fire>whatshot
fire-extinguisher>fire_extinguisher firefox>oi_firefox first-order>oi_first-order flag>flag!
flag-checkered>sports_score flag-o>flag flask>science flickr>oi_flickr floppy-o>save save>save
folder>folder! folder-o>folder folder-open>folder_open! folder-open-o>folder_open
font>font_download fonticons>oi_fonticons fort-awesome>oi_font-awesome forumbee>oi_forumbee
forward>fast_forward foursquare>oi_foursquare free-code-camp>oi_free-code-camp
frown-o>sentiment_sad futbol-o>sports_soccer soccer-ball-o>sports_soccer
gamepad>stadia_controller gavel>gavel legal>gavel gbp>currency_pound
genderless>radio_button_unchecked get-pocket>oi_get-pocket gg>oi_gg gg-circle>oi_gg-circle
gift>card_giftcard git>oi_git git-square>oi_git-square github>oi_github github-alt>oi_github-alt
github-square>oi_github-square gitlab>oi_gitlab gittip>oi_gittip gratipay>oi_gittip
glass>local_bar glide>oi_glide glide-g>oi_glide-g globe>public google>oi_google
google-plus>oi_google-plus google-plus-circle>oi_google-plus-circle
google-plus-official>oi_google-plus-circle google-plus-square>oi_google-plus-square
google-wallet>oi_google-wallet graduation-cap>school mortar-board>school grav>oi_grav
group>group! users>group! h-square>local_hospital hacker-news>oi_hacker-news
y-combinator-square>oi_hacker-news yc-square>oi_hacker-news hand-grab-o>back_hand
hand-rock-o>back_hand hand-lizard-o>oi_hand-lizard-o hand-o-down>arrow_downward
hand-o-left>arrow_back hand-o-right>arrow_forward hand-o-up>arrow_upward hand-paper-o>back_hand
hand-stop-o>back_hand hand-peace-o>oi_hand-peace-o hand-pointer-o>pan_tool_alt
hand-scissors-o>oi_hand-scissors-o hand-spock-o>oi_hand-spock-o handshake-o>handshake
hashtag>tag hdd-o>storage header>title headphones>headphones heart>favorite! heart-o>favorite
heartbeat>cardiology history>history home>home hospital-o>local_hospital
hourglass>hourglass_empty hourglass-1>hourglass_top hourglass-start>hourglass_top
hourglass-2>hourglass_bottom hourglass-half>hourglass_bottom hourglass-3>hourglass_disabled
hourglass-end>hourglass_disabled hourglass-o>hourglass_empty houzz>oi_houzz html5>oi_html5
i-cursor>text_fields id-badge>badge ils>₪ shekel>₪ sheqel>₪ image>image photo>image
picture-o>image imdb>oi_imdb inbox>inbox indent>format_indent_increase industry>factory
info>info info-circle>info! inr>currency_rupee rupee>currency_rupee instagram>oi_instagram
internet-explorer>oi_internet-explorer intersex>transgender transgender>transgender
ioxhost>oi_ioxhost italic>format_italic joomla>oi_joomla jsfiddle>oi_jsfiddle key>key
keyboard-o>keyboard krw>￦ won>￦ language>translate laptop>laptop lastfm>oi_lastfm
lastfm-square>oi_lastfm-square leaf>eco leanpub>oi_leanpub lemon-o>oi_lemon-o
level-down>subdirectory_arrow_right level-up>subdirectory_arrow_left life-bouy>support
life-buoy>support life-ring>support life-saver>support support>support lightbulb-o>lightbulb
line-chart>show_chart linkedin>oi_linkedin linkedin-square>oi_linkedin-square linode>oi_linode
linux>oi_linux list>format_list_bulleted list-alt>list_alt list-ol>format_list_numbered
list-ul>format_list_bulleted location-arrow>near_me lock>lock long-arrow-down>south
long-arrow-left>west long-arrow-right>east long-arrow-up>north low-vision>visibility_off
magic>wand_stars magnet>oi_magnet mail-forward>share share>share mail-reply>reply reply>reply
mail-reply-all>reply_all reply-all>reply_all male>male map>map map-marker>location_on map-o>map
map-pin>push_pin map-signs>signpost mars>male mars-double>oi_mars-double
mars-stroke>oi_mars-stroke mars-stroke-h>oi_mars-stroke-h mars-stroke-v>oi_mars-stroke-v
maxcdn>oi_maxcdn meanpath>oi_meanpath medium>oi_medium medkit>medical_services meetup>oi_meetup
meh-o>sentiment_neutral mercury>oi_mercury microchip>memory microphone>mic
microphone-slash>mic_off minus>remove minus-circle>remove_circle!
minus-square>indeterminate_check_box! minus-square-o>indeterminate_check_box
mixcloud>oi_mixcloud mobile>smartphone mobile-phone>smartphone modx>oi_modx money>payments
moon-o>dark_mode motorcycle>two_wheeler mouse-pointer>arrow_selector_tool! music>music_note
neuter>oi_neuter newspaper-o>newspaper object-group>select_all object-ungroup>deselect
odnoklassniki>oi_odnoklassniki odnoklassniki-square>oi_odnoklassniki-square opencart>oi_opencart
openid>oi_openid opera>oi_opera optin-monster>oi_optin-monster pagelines>oi_pagelines
paint-brush>brush paper-plane>send! send>send! paper-plane-o>send send-o>send
paperclip>attach_file paragraph>format_paragraph paste>content_paste pause>pause
pause-circle>pause_circle! pause-circle-o>pause_circle paw>pets paypal>oi_paypal pencil>edit!
pencil-square>edit_square! pencil-square-o>edit_square percent>percent phone>phone!
phone-square>phone! pie-chart>pie_chart pied-piper>oi_pied-piper
pied-piper-alt>oi_pied-piper-alt pied-piper-pp>oi_pied-piper-pp pinterest>oi_pinterest
pinterest-p>oi_pinterest-p pinterest-square>oi_pinterest-square plane>travel play>play_arrow
play-circle>play_circle! play-circle-o>play_circle plug>power plus>add plus-circle>add_circle!
plus-square>add_box! plus-square-o>add_box podcast>podcasts power-off>power_settings_new
print>print product-hunt>oi_product-hunt puzzle-piece>extension qq>oi_qq qrcode>qr_code
question>question_mark question-circle>help! question-circle-o>help_outline quora>oi_quora
quote-left>format_quote quote-right>format_quote ra>oi_ra rebel>oi_ra resistance>oi_ra
random>shuffle ravelry>oi_ravelry recycle>recycling reddit>oi_reddit
reddit-alien>oi_reddit-alien reddit-square>oi_reddit-square refresh>refresh registered>Ⓡ
renren>oi_renren repeat>redo rotate-right>redo retweet>repeat road>road rocket>rocket_launch
rotate-left>undo undo>undo rouble>currency_ruble rub>currency_ruble ruble>currency_ruble
rss-square>rss_feed safari>oi_safari scribd>oi_scribd search>search search-minus>zoom_out
search-plus>zoom_in sellsy>oi_sellsy server>dns share-alt>share! share-alt-square>share
share-square>share share-square-o>share shield>security ship>directions_boat
shirtsinbulk>oi_shirtsinbulk shopping-bag>shopping_bag shopping-basket>shopping_basket
shopping-cart>shopping_cart shower>shower sign-in>login sign-language>sign_language
signing>sign_language sign-out>logout signal>signal_cellular_4_bar simplybuilt>oi_simplybuilt
sitemap>account_tree skyatlas>oi_skyatlas skype>oi_skype slack>oi_slack sliders>tune
slideshare>oi_slideshare smile-o>sentiment_satisfied snapchat>oi_snapchat
snapchat-ghost>oi_snapchat-ghost snapchat-square>oi_snapchat-square snowflake-o>ac_unit
sort>swap_vert unsorted>swap_vert sort-alpha-asc>sort_by_alpha sort-alpha-desc>sort_by_alpha
sort-amount-asc>sort sort-amount-desc>sort sort-asc>arrow_upward sort-up>arrow_upward
sort-desc>arrow_downward sort-down>arrow_downward sort-numeric-asc>sort sort-numeric-desc>sort
soundcloud>oi_soundcloud space-shuttle>rocket spinner>progress_activity spoon>restaurant
spotify>oi_spotify square>square! square-o>square stack-exchange>oi_stack-exchange
stack-overflow>oi_stack-overflow star>star! star-half>star_half star-half-empty>star_half
star-half-full>star_half star-half-o>star_half star-o>star steam>oi_steam
steam-square>oi_steam-square step-backward>skip_previous step-forward>skip_next
stethoscope>stethoscope sticky-note>sticky_note_2! sticky-note-o>sticky_note_2 stop>stop
stop-circle>stop_circle! stop-circle-o>stop_circle street-view>streetview
strikethrough>strikethrough_s stumbleupon>oi_stumbleupon
stumbleupon-circle>oi_stumbleupon-circle subscript>subscript subway>subway suitcase>luggage
sun-o>light_mode superpowers>oi_superpowers superscript>superscript table>table_chart
tablet>tablet tag>label tags>sell tasks>checklist telegram>oi_telegram television>tv tv>tv
tencent-weibo>oi_tencent-weibo terminal>terminal text-height>height text-width>width
th>grid_view th-large>view_module th-list>view_list themeisle>oi_themeisle
thermometer>device_thermostat thermometer-4>device_thermostat thermometer-full>device_thermostat
thermometer-0>device_thermostat thermometer-empty>device_thermostat
thermometer-1>device_thermostat thermometer-quarter>device_thermostat
thermometer-2>device_thermostat thermometer-half>device_thermostat
thermometer-3>device_thermostat thermometer-three-quarters>device_thermostat thumb-tack>push_pin
thumbs-down>thumb_down! thumbs-o-down>thumb_down thumbs-o-up>thumb_up thumbs-up>thumb_up!
ticket>confirmation_number times-circle>cancel! times-circle-o>cancel times-rectangle>cancel!
window-close>cancel! times-rectangle-o>cancel window-close-o>cancel tint>water_drop
toggle-off>toggle_off toggle-on>toggle_on trademark>oi_trademark train>train
transgender-alt>transgender trash>delete! trash-o>delete tree>park trello>oi_trello
tripadvisor>oi_tripadvisor trophy>trophy! truck>local_shipping try>currency_lira
turkish-lira>currency_lira tty>tty tumblr>oi_tumblr tumblr-square>oi_tumblr-square
twitch>oi_twitch twitter>oi_x twitter-square>oi_x-square umbrella>umbrella
underline>format_underlined universal-access>accessibility unlock>lock_open
unlock-alt>no_encryption upload>upload usb>usb user>person! user-circle>account_circle!
user-circle-o>account_circle user-md>medical_services user-o>person user-plus>person_add!
user-secret>oi_user-secret user-times>person_remove! venus>female venus-double>oi_venus-double
venus-mars>oi_venus-mars viacoin>oi_viacoin viadeo>oi_viadeo viadeo-square>oi_viadeo-square
video-camera>videocam! vimeo>oi_vimeo vimeo-square>oi_vimeo-square vine>oi_vine vk>oi_vk
volume-control-phone>phone_in_talk volume-down>volume_down volume-off>volume_off
volume-up>volume_up wechat>oi_wechat weixin>oi_wechat weibo>oi_weibo whatsapp>oi_whatsapp
wheelchair>accessible wheelchair-alt>accessible_forward wifi>wifi wikipedia-w>oi_wikipedia-w
window-maximize>fullscreen window-minimize>minimize window-restore>fullscreen_exit
windows>oi_windows wordpress>oi_wordpress wpbeginner>oi_wpbeginner wpexplorer>oi_wpexplorer
wpforms>oi_wpforms wrench>build xing>oi_xing xing-square>oi_xing-square
y-combinator>oi_y-combinator yc>oi_y-combinator yahoo>oi_yahoo yelp>oi_yelp youtube>oi_youtube
youtube-play>oi_youtube-play youtube-square>oi_youtube-square tiktok>oi_tiktok
discord>oi_discord google-play>oi_google-play strava>oi_strava bluesky>oi_bluesky
kickstarter>oi_kickstarter threads>oi_threads
""")

OI_TO_MATERIAL = _parse_icon_map("""
text-break>format_image_front text-inline>format_image_inline_left voip>tty! search>search
group>stacks settings-adjust>tune apps>apps panel-right>dock_to_left launch>open_in_browser
text-wrap>text_wrap gif-picker>gif_box chevron-down>keyboard_arrow_down
chevron-left>chevron_backward chevron-right>chevron_forward chevron-up>keyboard_arrow_up
arrows-h>arrow_range arrows-v>height arrow-down-left>south_west arrow-down-right>south_east
arrow-down>south arrow-left>west arrow-right>east arrow-up-left>north_west
arrow-up-right>north_east arrow-up>north draggable>drag_indicator view>toolbar archive>archive
unarchive>unarchive text-effect>stylus_laser_pointer smile-add>add_reaction close>close_small
food-delivery>shopping_bag_speed schedule-today>early_on schedule-tomorrow>event_upcoming
schedule-later>calendar_clock activity>schedule activity-plus>alarm_add numpad>dialpad
transfer>sync_alt suitcase>work suitcase-plus>person_add merge>call_merge record>graphic_eq
backspace-o>backspace user>person! user-plus>person_add! users>group! ellipsis-h>more_horiz
ellipsis-v>more_vert plus>add minus>remove star-plus>star subtitle>subtitles
bring-front>flip_to_front send-back>flip_to_back life-ring-plus>support view-list>view_list
view-kanban>view_kanban threads>oi_threads kickstarter>oi_kickstarter x>oi_x
x-square>oi_x-square tiktok>oi_tiktok bluesky>oi_bluesky google-play>oi_google-play
strava>oi_strava discord>oi_discord view-pivot>oi_view-pivot view-cohort>oi_view-cohort
studio>oi_studio odoo>oi_odoo
""")

AMBIGUOUS_FILLED_ICONS = _ambiguous_filled_icons()
