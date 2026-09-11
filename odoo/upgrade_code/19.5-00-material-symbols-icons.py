"""Migrate FontAwesome / odoo-ui-icons markup to the Material Symbols system.

``<i class="fa fa-user"/>`` becomes ``<i class="oi" data-icon="person"/>``, and
the icon names carried by attributes, dict entries, JS strings and CSS
selectors are converted alike. This is a best-effort rewrite: dynamically built
class names and icons stored in data need a manual pass.
"""

from __future__ import annotations

import re
import typing
from functools import partial

from odoo.upgrade_code.material_symbols_icons_mapping import (
    AMBIGUOUS_FILLED_ICONS,
    FA_NOOP_MODIFIERS,
    FA_TO_MATERIAL,
    FA_UTIL_TO_OI,
    OI_TO_MATERIAL,
    OI_UTIL_CLASSES,
)

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager


def _lookup(cls: str) -> tuple[str, bool] | None:
    """Return (icon, filled) for an icon class such as ``fa-user``."""
    prefix, _, name = cls.partition('-')
    if prefix == 'fa':
        return FA_TO_MATERIAL.get(name)
    if prefix == 'oi':
        return OI_TO_MATERIAL.get(name)
    return None


def _modifier(cls: str) -> str | None:
    """Return the oi-* counterpart of a modifier class, '' when it carries nothing over."""
    if cls in OI_UTIL_CLASSES:
        return cls
    prefix, _, name = cls.partition('-')
    if prefix != 'fa':
        return None
    if name in FA_NOOP_MODIFIERS:
        return ''
    return FA_UTIL_TO_OI.get(name)


def _first_icon(class_value: str) -> tuple[str, bool] | None:
    """Return (icon, filled) for the first icon class of a class string."""
    for cls in class_value.split():
        if icon := _lookup(cls):
            return icon
    return None


def _icon_name(class_value: str) -> str | None:
    """Return the Material Symbols name of the first icon class of a class string."""
    icon = _first_icon(class_value)
    return icon and icon[0]


def _filled_suffix(fa_name: str) -> str:
    """Return the selector suffix telling the filled and outlined variants of an icon apart."""
    icon, filled = FA_TO_MATERIAL[fa_name]
    if icon in AMBIGUOUS_FILLED_ICONS:
        return '.oi-filled' if filled else ':not(.oi-filled)'
    return ''


def _split_classes(classes: list[str]) -> tuple[tuple[str, bool] | None, list[str], list[str]]:
    """Split into ((icon, filled) of the first icon class, oi modifiers, classes to keep)."""
    icon, modifiers, others = None, [], []
    for cls in classes:
        if cls in ('fa', 'oi'):
            continue
        if icon is None and (icon := _lookup(cls)):
            continue
        if (modifier := _modifier(cls)) is not None:
            if modifier:
                modifiers.append(modifier)
        else:
            others.append(cls)
    return icon, modifiers, others


def _build_classes(modifiers: list[str], others: list[str], filled: bool) -> str:
    """Join the ``oi`` class, its deduplicated modifiers and the untouched classes."""
    if filled:
        modifiers = [*modifiers, 'oi-filled']
    return ' '.join(['oi', *dict.fromkeys(modifiers), *others])


def _class_to_icon(class_value: str) -> tuple[str, str] | None:
    """Return (new class value, data-icon value) for an icon class string."""
    classes = class_value.split()
    if {'fa', 'oi'}.isdisjoint(classes):
        return None
    icon, modifiers, others = _split_classes(classes)
    if icon is None:
        return None
    name, filled = icon
    return _build_classes(modifiers, others, filled), name


def _fa_classes_to_oi(class_value: str) -> str | None:
    """Convert a fa-* class string to oi-* modifiers, dropping the icon class."""
    classes = class_value.split()
    if 'fa' not in classes:
        return None
    _icon, modifiers, others = _split_classes(classes)
    return _build_classes(modifiers, others, False)


# A whole opening tag, quoted attribute values included so that a '>' inside an
# expression (t-on-click="() => ...") does not end the match early.
TAG_RE = re.compile(r"""<[A-Za-z][\w.:-]*(?:[^>"']|"[^"]*"|'[^']*')*>""", re.DOTALL)
CLASS_ATTR_RE = re.compile(r"""(?<![-\w])class=(["'])(.*?)\1""", re.DOTALL)
T_ATT_CLASS_RE = re.compile(r"""\bt-att-class=(["'])(.*?)\1""", re.DOTALL)
T_ATTF_CLASS_RE = re.compile(r"""\bt-attf-class=(["'])(.*?)\1""", re.DOTALL)
DATA_ICON_RE = re.compile(r'\b(?:data-icon|t-att-data-icon|t-attf-data-icon)\s*=')
T_ATT_DATA_ICON_RE = re.compile(r'\bt-att-data-icon\s*=')
T_ATTF_DATA_ICON_RE = re.compile(r'\bt-attf-data-icon\s*=')
TEMPLATE_BLOCK_RE = re.compile(r'#\{.*?\}|\{\{.*?\}\}', re.DOTALL)
QUOTED_RE = re.compile(r"'([^']*)'")
# fa-fw, fa-2x, fa-1x… left over on an element that already renders through oi
FA_MODIFIER_RE = re.compile(
    r'(?<![\w-])fa-(%s)(?![\w-])'
    % '|'.join(sorted(
        map(re.escape, (*FA_UTIL_TO_OI, *FA_NOOP_MODIFIERS)), key=len, reverse=True,
    )),
)
OI_SIGNAL_RE = re.compile(r'(?<![\w-])oi(?:-\w+)?(?![\w-])')


def _replace(tag: str, match: re.Match, text: str) -> str:
    """Replace the span of ``match`` in ``tag`` by ``text``."""
    return tag[:match.start()] + text + tag[match.end():]


def _append_attribute(tag: str, attribute: str) -> str:
    """Add ``attribute`` at the end of an opening or self-closing tag."""
    if tag.endswith('/>'):
        return f'{tag[:-2]} {attribute}/>'
    return f'{tag[:-1]} {attribute}>'


def _strip_icon_from_class(tag: str) -> str:
    """Drop the icon of a static fa-* ``class``, now carried by a dynamic attribute."""
    match = CLASS_ATTR_RE.search(tag)
    if not match or '{' in match.group(2):
        return tag
    classes = _fa_classes_to_oi(match.group(2))
    if classes is None:
        return tag
    quote = match.group(1)
    return _replace(tag, match, f'class={quote}{classes}{quote}')


def _rewrite_class_attr(tag: str) -> str:
    """``class="fa fa-user"`` → ``class="oi oi-filled" data-icon="person"``."""
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
    return _replace(tag, match, f'class={quote}{classes}{quote} data-icon={quote}{icon}{quote}')


def _rewrite_t_att_class(tag: str) -> str:
    """``t-att-class="x ? 'fa-eye' : 'fa-eye-slash'"`` → ``t-att-data-icon=...``

    Only when every quoted literal of the expression is an icon class.
    """
    match = T_ATT_CLASS_RE.search(tag)
    if not match or T_ATT_DATA_ICON_RE.search(tag):
        return tag
    quote, expression = match.groups()
    icons = {literal: _icon_name(literal) for literal in QUOTED_RE.findall(expression)}
    if not icons or None in icons.values():
        return tag
    expression = QUOTED_RE.sub(lambda m: f"'{icons[m.group(1)]}'", expression)
    tag = _replace(tag, match, f't-att-data-icon={quote}{expression}{quote}')
    return _strip_icon_from_class(tag)


def _convert_static_classes(static: str) -> tuple[str, str | None]:
    """Convert the static head of a ``t-attf-class``, returning its icon if any."""
    classes, trailing = static.strip(), static[len(static.rstrip()):]
    if result := _class_to_icon(classes):
        return result[0] + trailing, result[1]
    if (classes := _fa_classes_to_oi(classes)) is not None:
        return classes + trailing, None
    return static, None


def _convert_block(block: str) -> tuple[str, str] | None:
    """Split a ``#{...}`` block made of icon literals into its (data-icon, class) parts."""
    opening, closing = ('#{', '}') if block.startswith('#{') else ('{{', '}}')
    inner = block[len(opening):-len(closing)]
    literals = QUOTED_RE.findall(inner)
    icons = {literal: _icon_name(literal) for literal in literals}
    if not icons or None in icons.values():
        return None
    residuals = {
        literal: ' '.join(
            cls for cls in literal.split() if cls not in ('fa', 'oi') and _lookup(cls) is None
        )
        for literal in literals
    }

    def substitute(values):
        return opening + QUOTED_RE.sub(lambda m: f"'{values[m.group(1)]}'", inner) + closing
    return substitute(icons), substitute(residuals)


def _rewrite_t_attf_class(tag: str) -> str:
    """Convert the static part of a ``t-attf-class`` and extract its icon.

    ``"fa fa-fw #{x ? 'fa-lock' : 'fa-unlock'}"`` becomes
    ``"oi oi-fw #{x ? '' : ''}"`` plus ``t-attf-data-icon="#{x ? 'lock' : 'lock_open'}"``.
    """
    match = T_ATTF_CLASS_RE.search(tag)
    if not match or T_ATTF_DATA_ICON_RE.search(tag):
        return tag
    quote, value = match.groups()
    blocks = list(TEMPLATE_BLOCK_RE.finditer(value))
    static_end = blocks[0].start() if blocks else len(value)
    static, static_icon = _convert_static_classes(value[:static_end])
    converted = [_convert_block(block.group(0)) for block in blocks]

    if blocks and None not in converted:
        classes, end = [static], static_end
        for block, (_icon, block_classes) in zip(blocks, converted):
            classes += [value[end:block.start()], block_classes]
            end = block.end()
        classes.append(value[end:])
        tag = _replace(tag, match, f"t-attf-class={quote}{''.join(classes)}{quote}")
        icons = ' '.join(icon for icon, _classes in converted)
        return _append_attribute(tag, f't-attf-data-icon="{icons}"')

    tag = _replace(tag, match, f't-attf-class={quote}{static}{value[static_end:]}{quote}')
    tag = _strip_icon_from_class(tag)
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
        if cls in OI_UTIL_CLASSES and cls in deduped:
            continue
        deduped.append(cls)
    if deduped == original:
        return tag
    quote = match.group(1)
    return _replace(tag, match, f"class={quote}{' '.join(deduped)}{quote}")


def _rewrite_tags(content: str) -> str:
    """Rewrite the icon classes of every opening tag in ``content``."""
    def rewrite(match: re.Match) -> str:
        tag = match.group(0)
        tag = _rewrite_class_attr(tag)
        tag = _rewrite_t_att_class(tag)
        tag = _rewrite_t_attf_class(tag)
        return _normalize_modifiers(tag)
    return TAG_RE.sub(rewrite, content)


# `icon=` of buttons, stat buttons, fields and OWL props
ICON_ATTR_RE = re.compile(r"""(\sicon=\s*)(["'])('[^']*'|[\w\s-]+)\2""")


def _icon_attr_sub(match: re.Match) -> str:
    """``icon="fa-star"`` → ``icon="star" icon_class="oi-filled"``.

    The modifiers move to the class attribute as well.
    """
    prefix, quote, value = match.groups()
    # OWL props hold a JS expression: icon="'fa-user'"
    is_prop = value.startswith("'") and value.endswith("'")
    icon, modifiers, others = _split_classes((value[1:-1] if is_prop else value).split())
    if icon is None:
        return match.group(0)
    name, filled = icon
    if filled:
        modifiers.insert(0, 'oi-filled')
    extras = ' '.join(modifiers + [cls for cls in others if not cls.startswith('fa-')])

    if is_prop:
        result = f"{prefix}{quote}'{name}'{quote}"
        return result + (f''' iconClass="'{extras}'"''' if extras else '')
    result = f'{prefix}{quote}{name}{quote}'
    return result + (f' icon_class="{extras}"' if extras else '')


# ``'icon': 'fa fa-user'`` dict entries, in view attributes, Python and JS. The
# key of the older ``'iconClass': 'fa-user'`` spelling held the icon itself.
DICT_ICON_RE = re.compile(
    r"""(?<![\w-])(?P<kq>['"]?)(?:icon|iconClass)(?P=kq)\s*:\s*"""
    r"""(?P<q>['"])(?P<value>(?:fa|oi)[\w\s-]*)(?P=q)""",
)


def _dict_icon_sub(match: re.Match, class_key: str | None) -> str:
    """``'icon': 'fa fa-star'`` → ``'icon': 'star'``, plus ``class_key: 'oi-filled'`` if given."""
    kq, quote = match.group('kq'), match.group('q')
    icon = _first_icon(match.group('value'))
    if icon is None:
        return match.group(0)
    name, filled = icon
    result = f'{kq}icon{kq}: {quote}{name}{quote}'
    if filled and class_key:
        result += f', {kq}{class_key}{kq}: {quote}oi-filled{quote}'
    return result


# in stylesheets, but also in test helpers and querySelector calls
SELECTOR_FA_RE = re.compile(r'(?:\.fa)?\.fa-([\w-]+)(?![\w-])')
SELECTOR_OI_RE = re.compile(r'\.oi-([\w-]+)(?![\w-])')


def _selector_fa_sub(match: re.Match, quote: str) -> str:
    """``.fa-star`` → ``[data-icon='star']``, and ``.fa-spin`` → ``.oi-spin``."""
    name = match.group(1)
    if name in FA_TO_MATERIAL:
        return f'[data-icon={quote}{FA_TO_MATERIAL[name][0]}{quote}]{_filled_suffix(name)}'
    if name in FA_UTIL_TO_OI:
        return f'.{FA_UTIL_TO_OI[name]}'
    return match.group(0)


def _selector_oi_sub(match: re.Match, quote: str) -> str:
    """``.oi-archive`` → ``[data-icon='archive']``."""
    name = match.group(1)
    if name in OI_TO_MATERIAL:
        return f'[data-icon={quote}{OI_TO_MATERIAL[name][0]}{quote}]'
    return match.group(0)


def _rewrite_selectors(content: str, quote: str = "'") -> str:
    """Rewrite the fa-* and oi-* class selectors, quoting ``data-icon`` values with ``quote``."""
    content = SELECTOR_FA_RE.sub(partial(_selector_fa_sub, quote=quote), content)
    return SELECTOR_OI_RE.sub(partial(_selector_oi_sub, quote=quote), content)


JS_ICON_FIELD_RE = re.compile(
    r"""(\b(?:icon|prefixIcon|titleIcon|done_icon)\b["']?\s*[:=]\s*)(["'])((?:fa|oi)[\w\s-]*)\2""",
)
JS_STRING_RE = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'')
# class manipulation needs the literal class name, not an icon name
CLASS_MANIP_RE = re.compile(r'\b(?:classList|className)\b|\w+Class\(')
TO_HAVE_CLASS_RE = re.compile(r'\btoHaveClass\((["\'])((?:fa )?fa-[\w-]+)\1\)')


def _js_icon_field_sub(match: re.Match) -> str:
    """``icon: "fa fa-user"`` → ``icon: "person"``."""
    prefix, quote, value = match.groups()
    icon = _icon_name(value)
    return f'{prefix}{quote}{icon}{quote}' if icon else match.group(0)


def _pure_icon_string(value: str) -> str | None:
    """Return the icon when ``value`` is made of icon classes only.

    Strings carrying unrelated classes (``"fa fa-user text-danger"``) are left
    alone: they are class lists, not icon names.
    """
    icon = None
    for cls in value.split():
        if cls in ('fa', 'oi') or _modifier(cls) is not None:
            continue
        found = _lookup(cls)
        if found is None or icon:
            return None
        icon = found[0]
    return icon


def _in_class_manipulation(content: str, position: int) -> bool:
    """Whether the statement around ``position`` manipulates classes, which need the class name."""
    # the statement may open lines above, as in a multi-line `classList.add(...)`
    window = max(0, position - 300)  # bounded, to stay linear
    statement_start = max(content.rfind(character, window, position) for character in ';{}') + 1
    line_end = content.find('\n', position)
    statement = content[max(statement_start, window):line_end if line_end != -1 else None]
    return bool(CLASS_MANIP_RE.search(statement))


def _is_object_key(content: str, start: int, end: int) -> bool:
    """Whether the literal is a toggled class, as in ``{ "fa-compress": fullscreen }``."""
    start -= 1
    while start >= 0 and content[start].isspace():
        start -= 1
    while end < len(content) and content[end].isspace():
        end += 1
    before = content[start] if start >= 0 else ''
    return content[end:end + 1] == ':' and before in '{,('


def _rewrite_icon_strings(content: str) -> str:
    """Replace the JS string literals made of icon classes only by their icon name."""
    def rewrite(match: re.Match) -> str:
        literal = match.group(0)
        if _in_class_manipulation(content, match.start()) or _is_object_key(content, *match.span()):
            return literal
        icon = _pure_icon_string(literal[1:-1])
        return f'{literal[0]}{icon}{literal[0]}' if icon else literal
    return JS_STRING_RE.sub(rewrite, content)


def _to_have_class_sub(match: re.Match) -> str:
    """``toHaveClass("fa-user")`` → ``toHaveAttribute("data-icon", "person")``."""
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


# icons of the website rating snippet live in their own attribute
RATING_ICON_RE = re.compile(
    r'(<[^>]*\bclass="[^"]*s_rating[^"]*"[^>]*)\bdata-icon="fa-([a-z][a-z0-9-]*)"',
)
COMPONENT_TAG_RE = re.compile(r"""<[A-Z][\w.]*(?:[^>"']|"[^"]*"|'[^']*')*>""", re.DOTALL)
ICON_CLASS_RE = re.compile(r'(?<![\w])icon_class(?![\w])')
SCSS_FA_CLASS_RE = re.compile(r'''(?<!['"])\.fa(?![\w-])''')


def transform_xml(content: str) -> str:
    """Migrate the icons of a view, template or data file."""
    content = _rewrite_tags(content)
    content = ICON_ATTR_RE.sub(_icon_attr_sub, content)
    content = DICT_ICON_RE.sub(partial(_dict_icon_sub, class_key='icon_class'), content)
    content = RATING_ICON_RE.sub(lambda m: f'{m.group(1)}data-rating-icon="{m.group(2)}"', content)
    # the attributes of a component tag are OWL props, camelCased
    return COMPONENT_TAG_RE.sub(lambda m: ICON_CLASS_RE.sub('iconClass', m.group(0)), content)


def transform_js(content: str, is_test: bool) -> str:
    """Migrate the icons of a JS file; ``is_test`` rewrites assertions instead of icon strings."""
    content = _rewrite_tags(content)  # markup in template literals
    content = ICON_ATTR_RE.sub(_icon_attr_sub, content)
    # no iconClass is added here: an unexpected key would break OWL prop validation
    content = DICT_ICON_RE.sub(partial(_dict_icon_sub, class_key=None), content)
    content = JS_ICON_FIELD_RE.sub(_js_icon_field_sub, content)
    content = _rewrite_selectors_in_js(content)
    if is_test:
        # a test asserts on the rendered markup, not on an icon name
        content = TO_HAVE_CLASS_RE.sub(_to_have_class_sub, content)
    else:
        content = _rewrite_icon_strings(content)
    return content


def transform_python(content: str) -> str:
    """Migrate the icons of ``Markup()`` literals and ``icon`` dict entries."""
    content = _rewrite_tags(content)  # markup in Markup() literals
    return DICT_ICON_RE.sub(partial(_dict_icon_sub, class_key='iconClass'), content)


def transform_scss(content: str) -> str:
    """Migrate the icon selectors of a stylesheet."""
    return _rewrite_selectors(SCSS_FA_CLASS_RE.sub('.oi', content))


# `web` defines the icon system itself: its remaining fa-* references describe
# the migration, they are not markup to migrate.
SKIPPED_ADDONS = frozenset({'web'})
# vendored code, which follows its own upstream
SKIPPED_DIRECTORIES = frozenset({'lib', 'node_modules', 'o_spreadsheet'})


def upgrade(file_manager: FileManager):
    """Migrate the icons of every addon file, vendored code and ``web`` excepted."""
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


def test(transform, content, expected):
    """Assert that ``transform`` converts ``content`` into ``expected``."""
    output = transform(content)
    assert output == expected, f"Failed to convert {content!r}; got {output!r} instead of {expected!r}"


if __name__ == '__main__':
    """Quick test suite (silent on success). Run with:
    PYTHONPATH=. python odoo/upgrade_code/19.5-00-material-symbols-icons.py
    """
    js, js_test = partial(transform_js, is_test=False), partial(transform_js, is_test=True)
    test(transform_xml, '<i class="fa fa-user fa-fw text-muted"/>', '<i class="oi oi-fw oi-filled text-muted" data-icon="person"/>')
    test(transform_xml, '<i class="fa fa-star fa-1x"/>', '<i class="oi oi-filled" data-icon="star"/>')
    test(transform_xml, '<i class="oi oi-archive"/>', '<i class="oi" data-icon="archive"/>')
    test(transform_xml, '<i class="fa-user"/>', '<i class="fa-user"/>')
    test(transform_xml, '<span class="fa fa-lg" t-att-class="x ? \'fa-eye\' : \'fa-eye-slash\'"/>', '<span class="oi oi-lg" t-att-data-icon="x ? \'visibility\' : \'visibility_off\'"/>')
    test(transform_xml, '<i t-attf-class="fa fa-fw #{x ? \'fa-lock\' : \'fa-unlock\'}"/>', '<i t-attf-class="oi oi-fw #{x ? \'\' : \'\'}" t-attf-data-icon="#{x ? \'lock\' : \'lock_open\'}"/>')
    test(transform_xml, '<i t-attf-class="fa fa-user #{cls}"/>', '<i t-attf-class="oi oi-filled #{cls}" data-icon="person"/>')
    test(transform_xml, '<button icon="fa-star" string="a"/>', '<button icon="star" icon_class="oi-filled" string="a"/>')
    test(transform_xml, '<button icon="fa-user-o"/>', '<button icon="person"/>')
    test(transform_xml, '<Foo icon="\'fa-star\'"/>', '<Foo icon="\'star\'" iconClass="\'oi-filled\'"/>')
    test(transform_xml, '<field name="a" options="{\'icon\': \'fa fa-star\'}"/>', '<field name="a" options="{\'icon\': \'star\', \'icon_class\': \'oi-filled\'}"/>')
    test(transform_python, "{'icon': 'fa fa-star'}", "{'icon': 'star', 'iconClass': 'oi-filled'}")
    test(js, 'const a = { icon: "fa fa-star" };', 'const a = { icon: "star" };')
    test(js, 'return "fa fa-phone";', 'return "phone";')
    test(js, 'return "fa fa-phone text-danger";', 'return "fa fa-phone text-danger";')
    test(js, 'el.classList.add("fa-phone");', 'el.classList.add("fa-phone");')
    test(js, 'const c = { "fa-compress": full };', 'const c = { "fa-compress": full };')
    test(js, "querySelector('.fa-star')", 'querySelector(\'[data-icon="star"].oi-filled\')')
    test(js_test, 'expect(el).toHaveClass("fa-user");', 'expect(el).toHaveAttribute("data-icon", "person");')
    test(transform_scss, '.fa.fa-star-o, .fa-spin { }', ".oi[data-icon='star']:not(.oi-filled), .oi-spin { }")
    test(transform_scss, '.o_x .fa { }', '.o_x .oi { }')
