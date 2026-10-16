# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import re

from lxml import etree
from markupsafe import Markup, escape

from odoo import _

PREVIEW_CSS_CLASS = 'o_account_edi_xml_preview'
TABLE_CLASS = 'table table-sm table-bordered table-hover mb-0'
# overflow-hidden is required so table-bordered cells clip to the radius.
TABLE_WRAP_CLASS = 'rounded-2 overflow-hidden'
SKIP_LOCALNAMES = frozenset({
    'Signature',
    'UBLExtensions',
    'EmbeddedDocumentBinaryObject',
})
MAX_DEPTH = 12
MAX_NODES = 1500
MAX_TEXT_LEN = 400
MIN_REPEAT = 2
_BASE64_HEAD = re.compile(r'^[A-Za-z0-9+/=\s]{40,}$')


def preview_token(attachment_id, filename):
    """Stable idempotence key stored in the note HTML. Hex only, so it is not an ilike wildcard."""
    digest = hashlib.sha1((filename or '').encode()).hexdigest()[:16]
    return '%s-%s' % (attachment_id or 0, digest)


def xml_tree_to_html(tree, filename='', token=''):
    """Render an lxml element as nested Bootstrap tables. Returns a Markup, or empty."""
    if tree is None:
        return Markup()
    root = tree if not hasattr(tree, 'getroot') else tree.getroot()
    stats = {'nodes': 0}
    body = _render_hybrid(root, depth=0, stats=stats)
    if not body:
        return Markup()
    title = Markup('%s - %s - %s') % (
        _("Electronic document XML"),
        filename or '',
        etree.QName(root).localname,
    )
    return Markup(
        '<div class="%s">'
        '<span style="display:none">account-xml-preview:%s</span>'
        '<p class="mb-1"><strong>%s</strong></p>'
        '<div data-o-mail-quote="1">%s</div>'
        '</div>'
    ) % (escape(PREVIEW_CSS_CLASS), escape(token), title, body)


def _xml_children(element):
    return [
        child for child in element
        if isinstance(child.tag, str) and etree.QName(child).localname not in SKIP_LOCALNAMES
    ]


def _is_leaf(element):
    return not _xml_children(element)


def _tag_label(element):
    local = etree.QName(element).localname
    prefix = element.prefix
    if prefix:
        return Markup('<span class="text-muted">%s:</span>%s') % (prefix, local)
    return local


def _clip_text(value):
    text = value if isinstance(value, str) else str(value or '')
    if _is_binary_payload(text):
        return Markup('<em class="text-muted">%s</em>') % _("(binary omitted)")
    if len(text) > MAX_TEXT_LEN:
        text = text[:MAX_TEXT_LEN] + '...'
    return escape(text)


def _is_binary_payload(text):
    stripped = ''.join(text.split())
    if len(stripped) < 80:
        return False
    return bool(_BASE64_HEAD.match(text[:120])) and len(stripped) > MAX_TEXT_LEN


def _leaf_value(element):
    text = (element.text or '').strip()
    value = _clip_text(text) if text else Markup('<span class="text-muted">-</span>')
    extras = []
    for name, raw in element.attrib.items():
        extras.append(Markup('%s=%s') % (name, _clip_text(raw)))
    if extras:
        joined = Markup(' ').join(extras)
        return Markup('%s <span class="text-muted">%s</span>') % (value, joined)
    return value


def _group_children(children):
    groups = []
    for child in children:
        name = etree.QName(child).localname
        if groups and groups[-1][0] == name:
            groups[-1][1].append(child)
        else:
            groups.append([name, [child]])
    return groups


def _table(inner):
    """Wrap a table so Bootstrap rounded-2 actually clips the borders."""
    return Markup('<div class="%s">%s</div>') % (TABLE_WRAP_CLASS, inner)


def _kv_row(label, value):
    return Markup(
        '<tr><th class="table-light text-nowrap py-1" style="width:1%%">%s</th>'
        '<td class="py-1">%s</td></tr>'
    ) % (label, value)


def _wrap_card(label, inner):
    return _table(Markup(
        '<table class="%s">'
        '<thead class="table-light"><tr><th class="py-1">%s</th></tr></thead>'
        '<tbody><tr><td class="p-0">%s</td></tr></tbody></table>'
    ) % (TABLE_CLASS, label, inner))


def _inner_table(element, depth, stats):
    rows = _render_children_rows(element, depth, stats)
    if not rows:
        return Markup('')
    return _table(Markup('<table class="%s"><tbody>%s</tbody></table>') % (TABLE_CLASS, rows))


def _render_repeat_cards(name, items, depth, stats):
    """Render N sibling elements as numbered cards instead of a flat table."""
    if all(_is_leaf(item) for item in items):
        rows = Markup().join(
            Markup('<tr><td class="py-1">%s</td></tr>') % _leaf_value(item)
            for item in items
        )
        return _table(Markup(
            '<table class="%s"><thead class="table-light">'
            '<tr><th class="py-1">%s (%s)</th></tr></thead>'
            '<tbody>%s</tbody></table>'
        ) % (TABLE_CLASS, name, len(items), rows))
    cards = Markup()
    for idx, item in enumerate(items, 1):
        stats['nodes'] += 1
        if stats['nodes'] >= MAX_NODES or depth > MAX_DEPTH:
            cards += Markup('<em class="text-muted">...</em>')
            break
        label = Markup('%s #%s') % (name, idx)
        if _is_leaf(item):
            inner = _table(Markup('<table class="%s"><tbody>%s</tbody></table>') % (
                TABLE_CLASS, _kv_row(_tag_label(item), _leaf_value(item)),
            ))
        else:
            inner = _inner_table(item, depth + 1, stats)
        if inner:
            cards += _wrap_card(label, inner)
    return Markup('<div class="d-flex flex-column gap-1">%s</div>') % cards


def _render_children_rows(element, depth, stats):
    rows = Markup()
    for name, raw in element.attrib.items():
        rows += _kv_row(Markup('@%s') % name, _clip_text(raw))
    text = (element.text or '').strip()
    if text:
        rows += _kv_row('#text', _clip_text(text))
    if stats['nodes'] >= MAX_NODES or depth > MAX_DEPTH:
        return rows + Markup(
            '<tr><td colspan="2" class="py-1"><em class="text-muted">...</em></td></tr>'
        )
    for name, group in _group_children(_xml_children(element)):
        if len(group) >= MIN_REPEAT:
            rows += Markup('<tr><td class="p-0" colspan="2">%s</td></tr>') % (
                _render_repeat_cards(name, group, depth + 1, stats)
            )
            continue
        child = group[0]
        stats['nodes'] += 1
        if _is_leaf(child):
            rows += _kv_row(_tag_label(child), _leaf_value(child))
        else:
            rows += Markup('<tr><td class="p-0" colspan="2">%s</td></tr>') % (
                _wrap_card(
                    _tag_label(child),
                    _inner_table(child, depth + 1, stats),
                )
            )
    return rows


def _render_hybrid(element, depth, stats):
    if not isinstance(element.tag, str) or etree.QName(element).localname in SKIP_LOCALNAMES:
        return Markup()
    if stats['nodes'] >= MAX_NODES or depth > MAX_DEPTH:
        return Markup('<em class="text-muted">...</em>')
    stats['nodes'] += 1
    if _is_leaf(element):
        return _table(Markup('<table class="%s"><tbody>%s</tbody></table>') % (
            TABLE_CLASS,
            _kv_row(_tag_label(element), _leaf_value(element)),
        ))
    rows = _render_children_rows(element, depth, stats)
    if not rows:
        rows = Markup('<tr><td class="py-1" colspan="2">-</td></tr>')
    return _table(Markup(
        '<table class="%s"><thead class="table-light"><tr><th class="py-1" colspan="2">%s</th></tr></thead>'
        '<tbody>%s</tbody></table>'
    ) % (TABLE_CLASS, _tag_label(element), rows))
