from __future__ import annotations

import csv
import difflib
import logging
import re
import typing
from collections import defaultdict
from io import StringIO

import lxml.etree as etree

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager

_logger = logging.getLogger(__name__)

manual = {
    'base.ng': {'100': -1},
}


def template2country(template):
    return f"base.{template[:2]}"


def data_file_module_name(f):
    return f.path.parts[f.path.parts.index('data') - 1]


def tax_grouper(row_iter):
    current_batch = [next(row_iter)]
    for row in row_iter:
        if row['id']:
            yield current_batch
            current_batch = [row]
        else:
            current_batch.append(row)
    yield current_batch


def tag_factor(tax_rows):
    tag2factor = defaultdict(lambda: defaultdict(float))
    for row in tax_rows:
        document_type = row['repartition_line_ids/document_type']
        factor_percent = float(row.get('repartition_line_ids/factor_percent') or 100)
        if tags := row.get('repartition_line_ids/tag_ids'):
            for tag in tags.split('||'):
                tag2factor[document_type][tag] += factor_percent
    return tag2factor


def test_tag_signs(tag_signs):
    assert tag_signs['base.be']['03'] == -1, tag_signs['base.be']
    assert tag_signs['base.be']['49'] == 1, tag_signs['base.be']
    assert tag_signs['base.be']['54'] == -1, tag_signs['base.be']
    assert tag_signs['base.be']['62'] == 1, tag_signs['base.be']
    assert tag_signs['base.be']['64'] == 1, tag_signs['base.be']
    assert tag_signs['base.be']['81'] == 1, tag_signs['base.be']
    assert tag_signs['base.be']['85'] == -1, tag_signs['base.be']
    assert tag_signs['base.it']['4v'] == -1, tag_signs['base.it']


def remove_sign(tag_string, tag_signs, type_tax_use, document_type, tag2factor):
    tags = []
    if not tag_string:
        return tag_string
    for tag in tag_string.split('||'):
        tag = tag.strip()
        if not tag.startswith(('-', '+')):
            tags.append(tag)
            continue
        sign_str, new_tag = tag[0], tag[1:]
        tags.append(new_tag)

        if type_tax_use not in ('sale', 'purchase'):
            continue

        report_sign = 1 if sign_str == '+' else -1  # tax_negate
        if (type_tax_use, document_type) in [('sale', 'invoice'), ('purchase', 'refund')]:  # tax_tag_invert
            report_sign *= -1

        if existing_sign := tag_signs.get(new_tag):
            if existing_sign not in (report_sign, 'error'):
                tag_signs[new_tag] = 'error'
        else:
            tag_signs[new_tag] = report_sign

    return '||'.join(tags)


def upgrade(file_manager: FileManager):
    tax_template_files = [
        f for f in file_manager
        if f.path.suffix == '.csv'
        and f.path.parts[-2] == 'template'
        and f.path.stem.startswith('account.tax-')
    ]
    nb_template_files = len(tax_template_files)
    tax_report_files = [
        f for f in file_manager
        if f.path.suffix == '.xml'
        and 'data' in f.path.parts
        and data_file_module_name(f).startswith('l10n_')
    ]
    nb_report_files = len(tax_report_files)

    tag_signs = defaultdict(dict)
    for i, file in enumerate(tax_template_files):
        file_manager.print_progress(i, nb_template_files + nb_report_files, file.path)
        country = template2country(file.path.stem.split('-', maxsplit=1)[1])
        country_tax_signs = tag_signs[country]
        csv_file = csv.DictReader(file.content.splitlines())
        csv_data = list(csv_file)
        if 'repartition_line_ids/document_type' not in csv_data[0]:
            continue

        group_data = {}
        for row in csv_data:
            if row.get('amount_type') == 'group':
                for xmlid in row['children_tax_ids'].split(","):
                    assert xmlid not in group_data or group_data[xmlid] == row['type_tax_use']
                    group_data[xmlid] = row['type_tax_use']

        buffer = StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=csv_file.fieldnames,
            delimiter=',',
            quotechar='"',
            quoting=csv.QUOTE_ALL,
            lineterminator='\n',
        )
        writer.writeheader()
        for tax_rows in tax_grouper(iter(csv_data)):
            type_tax_use = tax_rows[0]['type_tax_use']
            if type_tax_use == 'none':
                type_tax_use = group_data.get(tax_rows[0]['id']) or 'none'
            assert type_tax_use
            tag2factor = tag_factor(tax_rows)
            for row in tax_rows:
                document_type = row['repartition_line_ids/document_type']
                writer.writerow({
                    fname: (
                        remove_sign(value, country_tax_signs, type_tax_use, document_type, tag2factor[document_type])
                        if fname == 'repartition_line_ids/tag_ids' else
                        value
                    )
                    for fname, value in row.items()
                })
        file.content = buffer.getvalue()

    conflicts = {}
    for country, country_tax_signs in tag_signs.items():
        if errors := [country for country, sign in country_tax_signs.items() if sign == 'error']:
            conflicts[country] = errors

    if conflicts:
        _logger.warning("\n\n\nInconsistent tag signs found:")
        for country in sorted(conflicts):
            _logger.warning("%s: %s", country, conflicts[country])

    # test_tag_signs(tag_signs)

    unknowns = defaultdict(list)
    for i, file in enumerate(tax_report_files):
        file_manager.print_progress(nb_template_files + i, nb_template_files + nb_report_files, file.path)
        tree = etree.parse(str(file.path))
        touch = False
        for report_node in tree.xpath("//record[@model='account.report']"):
            country_node = report_node.find("field[@name='country_id']")
            if country_node is None:
                continue
            country_code = country_node.attrib['ref']
            country_tax_signs = tag_signs[country_code]
            for expression_node in report_node.findall(".//record[@model='account.report.expression']"):
                engine_node = expression_node.find("field[@name='engine']")
                if engine_node.text == 'tax_tags':
                    formula_node = expression_node.find("field[@name='formula']")
                    tag = formula_node.text
                    if manual_sign := manual.get(country_code, {}).get(tag):
                        if manual_sign == -1:
                            touch = True
                            formula_node.text = '-' + formula_node.text
                    elif tag not in country_tax_signs:
                        unknowns[country_code].append(tag)
                    elif country_tax_signs[tag] == -1:
                        touch = True
                        formula_node.text = '-' + formula_node.text
        if touch:
            file.content = ''.join(
                diff[2:]
                for diff in difflib.ndiff(
                    file.content.splitlines(keepends=True),
                    etree.tostring(tree, encoding="utf-8").decode().splitlines(keepends=True),
                )
                # avoid any diff generated by lxml and only keep diff for the lines added
                if (
                    diff.startswith((' ', '-'))
                    or re.match(r"""\+\s*<field name=["']formula["']""", diff)
                ) and not re.match(r"""-\s*<field name=["']formula["']""", diff)
            )

    if unknowns:
        _logger.warning("\n\n\nUnknown tag signs found:")
        for country in sorted(unknowns):
            _logger.warning("%s: %s", country, unknowns[country])
