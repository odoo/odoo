from __future__ import annotations

import logging
import typing

from odoo.upgrade_code.tools_etree import update_etree

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager

_logger = logging.getLogger(__name__)

SHORTHAND_FORMULA_ENGINES = {
    'domain_formula': 'domain',
    'aggregation_formula': 'aggregation',
    'account_codes_formula': 'account_codes',
    'external_formula': 'external',
    'tax_tags_formula': 'tax_tags',
}


def _get_is_foldable(foldable_node):
    """Interpret the foldable value from the XML field node. Returns True or False."""
    eval_attr = foldable_node.get('eval')
    if eval_attr is not None:
        val = eval_attr.strip()
        if val in ('True', '1'):
            return True
        elif val in ('False', '0', 'None', ''):
            return False
    text = (foldable_node.text or '').strip()
    if text in ('True', '1'):
        return True
    elif text in ('False', '0', ''):
        return False
    return False


def _find_parent_report(record_node):
    """Walk up the XML tree to find the ancestor account.report record."""
    node = record_node.getparent()
    while node is not None:
        if node.tag == 'record' and node.get('model') == 'account.report':
            return node
        node = node.getparent()
    return None


def _has_groupby(node):
    """Check whether an XML record node has a non-empty groupby field."""
    if node is None:
        return False
    groupby_field = node.find("field[@name='groupby']")
    return groupby_field is not None and (
        (groupby_field.text and groupby_field.text.strip()) or groupby_field.get('eval')
    )


def _has_user_groupby(node):
    """Check whether an XML record node has a non-empty user_groupby field."""
    if node is None:
        return False
    user_groupby_field = node.find("field[@name='user_groupby']")
    return user_groupby_field is not None and (
        (user_groupby_field.text and user_groupby_field.text.strip()) or user_groupby_field.get('eval')
    )


def _compute_foldability_from_xml(record_node):
    """Replicate _compute_foldable logic using only the XML record structure."""
    # Check for children_ids
    children_field = record_node.find("field[@name='children_ids']")
    has_children = (
        children_field is not None
        and len(children_field.findall("record[@model='account.report.line']")) > 0
    )

    # Collect expression engines
    expression_engines = set()

    expressions_field = record_node.find("field[@name='expression_ids']")
    if expressions_field is not None:
        for expr_record in expressions_field.findall("record[@model='account.report.expression']"):
            engine_field = expr_record.find("field[@name='engine']")
            if engine_field.text:
                expression_engines.add(engine_field.text.strip())

    for field_name, engine in SHORTHAND_FORMULA_ENGINES.items():
        field_node = record_node.find(f"field[@name='{field_name}']")
        if field_node is not None and (field_node.text or field_node.get('eval')):
            expression_engines.add(engine)

    has_line_groupby = _has_groupby(record_node)
    has_line_user_groupby = _has_user_groupby(record_node)

    # Check the parent report's groupby (report_line.report_id.groupby)
    report_node = _find_parent_report(record_node)
    has_report_groupby = _has_groupby(report_node)
    has_report_user_groupby = _has_user_groupby(report_node)
    has_groupby = has_line_groupby or has_line_user_groupby or has_report_user_groupby or has_report_groupby

    if has_children:
        return 'always_unfolded'
    elif has_groupby and all(e not in ('external', 'aggregation') for e in expression_engines):
        return 'foldable'
    elif any(e in ('external', 'aggregation') for e in expression_engines):
        return 'never_unfoldable'
    else:
        return 'always_unfolded'


def _foldable_matches_compute(is_foldable, computed_value):
    """Check if the XML foldable value is consistent with _compute_foldability."""
    # Old Boolean True = "this line is foldable" -> matches 'foldable'
    if is_foldable is True and computed_value == 'foldable':
        return True
    # Old Boolean False = "this line is NOT foldable" -> matches 'never_unfoldable' or 'always_unfolded'
    return is_foldable is False and computed_value in ('never_unfoldable', 'always_unfolded')


def _remove_element(node):
    """Remove an element from its parent, properly bridging the surrounding whitespace."""
    prev = node.getprevious()
    if prev is not None:
        prev.tail = (prev.tail or '').rstrip() + (node.tail or '')
    else:
        parent = node.getparent()
        parent.text = (parent.text or '').rstrip() + (node.tail or '')
    node.getparent().remove(node)


def upgrade(file_manager: FileManager):
    files = [f for f in file_manager if f.path.suffix == '.xml']
    if not files:
        return

    inconsistencies = []

    for fileno, file in enumerate(files, start=1):
        if '<field name="foldable"' not in file.content:
            file_manager.print_progress(fileno, len(files), file.path)
            continue

        def process(root, _file=file):
            for record in root.iter('record'):
                if record.get('model') != 'account.report.line':
                    continue
                foldable_node = record.find("field[@name='foldable']")
                if foldable_node is None:
                    continue

                is_foldable = _get_is_foldable(foldable_node)
                computed_value = _compute_foldability_from_xml(record)

                if _foldable_matches_compute(is_foldable, computed_value):
                    _remove_element(foldable_node)
                elif is_foldable:
                    # Old Boolean True doesn't match compute; replace with
                    # the explicit selection value to preserve the intent.
                    foldable_node.text = 'foldable'
                    foldable_node.set('name', 'foldability')
                    for attr in list(foldable_node.attrib):
                        if attr != 'name':
                            del foldable_node.attrib[attr]
                else:
                    record_id = record.get('id', 'unknown')
                    inconsistencies.append(
                        f"  {_file.path}: record '{record_id}' has "
                        f"foldable='{is_foldable}' but compute gives '{computed_value}'"
                    )

        file.content = update_etree(file.content, process)
        file_manager.print_progress(fileno, len(files), file.path)

    if inconsistencies:
        summary = "Foldability inconsistencies found:\n" + "\n".join(inconsistencies)
        file_manager.add_to_summary(summary)
