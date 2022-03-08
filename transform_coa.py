#!/usr/bin/env python3

import glob
import io
import sys
import csv
import re
from itertools import groupby
from pathlib import Path

from lxml import etree

from odoo import Command
from odoo.tools.safe_eval import safe_eval

self = locals().get('self') or {}
env = locals().get('env') or {}


def pformat(item, level=0, stream=None):
    stream = stream or io.StringIO()
    if isinstance(item, (Field, Record)):
        stream.write(pformat(item.get('children', {}), level=level))
    elif isinstance(item, (tuple, list)):
        start, end = '[]' if isinstance(item, list) else '()'
        is_o2m = all([isinstance(sub, (tuple, list))
                      and 2 <= len(sub) <= 3
                      and all([isinstance(x, int) for x in sub[:2]])
                      for sub in item])
        stream.write(indent(level, start + '\n'))
        for i, subitem in enumerate(item):
            if is_o2m:
                subitem = list(subitem)
                if subitem == [5, 0, 0]:
                    value_str = Unquoted("Command.clear()")
                elif len(subitem) == 3 and isinstance(subitem[2], Record):
                    if subitem[0] == Command.CREATE:
                        value_str = Unquoted("Command.create(" + pformat(subitem[2], level+1).strip() + ")")
            else:
                value_str = repr(subitem)
            stream.write(indent(level + 1, f"{value_str}{',' if i < len(item) else ''}\n"))
        stream.write(indent(level, end))
    elif isinstance(item, dict):
        stream.write(indent(level, '{\n'))
        for i, (key, subitem) in enumerate(item.items()):
            if isinstance(subitem, Field):
                value = subitem._value
            else:
                value = subitem
            value_str = pformat(value, level + 1).lstrip()
            stream.write(indent(level + 1, f"{repr(key)}: {value_str}{',' if i < len(item) else ''}\n"))
        stream.write(indent(level, '}\n'))
    else:
        stream.write(indent(level, repr(item)))
    return stream.getvalue()


# Classes -----------------------------------------------

class Node(dict):
    def __init__(self, el):
        super().__init__({'id': el.get('id', el.get('name'))})

    def append(self, child):
        children = self.get('children') or []
        children.append(child)
        self['children'] = children

class Field(Node):
    def __init__(self, el):
        super().__init__(el)
        text = (el.get('text') or (hasattr(el, 'text') and el.text) or '').strip()
        ref = el.get('ref', '').strip()
        _eval = el.get('eval', '')
        if isinstance(_eval, str):
            _eval = _eval.strip()
        if text:
            self._value = text
            self.value_type = 'text'
        elif ref:
            self._value = Ref(ref)
            self.value_type = 'ref'
        elif _eval:
            self._value = safe_eval(_eval, globals_dict={'ref': Ref})
            self.value_type = 'eval'
        else:
            self._value = None
            self.value_type = None


# Records -----------------------------------------------

class Record(Node):
    _from = None
    def __init__(self, el, tag):
        super().__init__(el)
        self['tag'] = tag
        self['_model'] = el.get('model')
        mapping = {cls._from: cls for cls in Record.__subclasses__() if cls._from}
        target_cls = mapping.get(self['_model'])
        if target_cls:
            self.__class__ = target_cls

    def append(self, child):
        if not isinstance(child, Field):
            raise ValueError(f"Wrong child type {type(child)}")
        children = self.get('children') or {}
        child = self.cleanup(child)
        if not child.get('delete'):
            children[child.get('id')] = child
        self['children'] = children

    def cleanup(self, child):
        value = child._value
        record_id = child.get('id')
        if isinstance(value, str) and value.upper() in ('TRUE', 'FALSE', 'NONE'):
            child._value = {'TRUE': True, 'FALSE': False, 'NONE': None}.get(value.upper())
        elif record_id == 'sequence':
            child._value = int(child._value)
        elif record_id == 'amount':
            child._value = float(child._value)
        elif record_id == 'default_pos_receivable_account_id':
            child['id'] = 'account_default_pos_receivable_account_id'
        return child

    def cleanup_o2m(self, child, cls=None):
        value = child._value

        def cleanup_sub(fields, cls):
            sub = cls({'id': None, 'model': cls._from}, cls.__name__)
            for key, value in fields.items():
                sub.append(Field({'id': key, 'eval': repr(value)}))
            return sub

        if isinstance(value, (tuple, list)):
            for i, sub in enumerate(value):
                if (isinstance(sub, (list, tuple)) and
                    len(sub) == 3 and
                    sub[0] == Command.CREATE and
                    sub[1] == 0 and
                    isinstance(sub[2], dict)):
                    if cls:
                        sub = [sub[0], sub[1], cleanup_sub(sub[2], cls)]
                        value[i] = sub
                elif (isinstance(sub, (list, tuple)) and
                      len(sub) == 3 and
                      sub[0] == Command.SET and
                      sub[1] == 0 and
                      isinstance(sub[2], list)):
                    if cls:
                        sub = [sub[0], sub[1], [cleanup_sub(x, cls) for x in sub[2]]]
                        value[i] = sub
        return value

class Unquoted(str):
    def __init__(self, value):
        super().__init__()
        self._value = value
    def __repr__(self):
        return self._value

class TemplateData(Record):
    _from = 'account.chart.template'
    def cleanup(self, child):
        child = super().cleanup(child)
        record_id = child.get('id')
        if record_id in ('name'):
            child['delete'] = True
        return child

class ResCompany(Record):
    _from = 'res.company'
    def cleanup(self, child):
        child = super().cleanup(child)
        return child

class ResCountryGroup(Record):
    _from = 'res.country.group'
    def cleanup(self, child):
        child = super().cleanup(child)
        record_id = child.get('id')
        if record_id in ('country_ids'):
            child._value = self.cleanup_o2m(child)
        return child

class AccountTax(Record):
    _from = 'account.tax.template'
    def cleanup(self, child):
        child = super().cleanup(child)
        record_id = child.get('id')
        if record_id == 'chart_template_id':
            child['delete'] = True
        elif record_id == 'tax_group_id':
            child._value = Unquoted(f"f'account.{{cid}}_{child._value}'")
        elif record_id in ('invoice_repartition_line_ids', 'refund_repartition_line_ids'):
            child._value = self.cleanup_o2m(child, AccountTaxRepartitionLine)
        return child

class AccountTaxRepartitionLine(Record):
    _from = 'account.tax.repartition.line'
    def cleanup(self, child):
        child = super().cleanup(child)
        record_id = child.get('id')
        if record_id == 'account_id':
            child._value = Unquoted(f"f'account.{{cid}}_{child._value}'")
        return child

class AccountFiscalPosition(Record):
    _from = 'account.fiscal.position'
    def cleanup(self, child):
        child = super().cleanup(child)
        record_id = child.get('id')
        if child._value is None:
            child['delete'] = True
        elif record_id in ('country_id', 'country_group_id'):
            child._value = Ref(child._value)
        elif record_id in ('vat_required', 'auto_apply'):
            child._value = int(child._value)
        return child

class AccountTaxReport(Record):
    _from = 'account.tax.report'
    def cleanup(self, child):
        child = super().cleanup(child)
        record_id = child.get('id')
        if record_id == 'root_line_ids':
            child._value = self.cleanup_o2m(child)
        return child

class AccountTaxReportLine(Record):
    _from = 'account.tax.report.line'
    def cleanup(self, child):
        child = super().cleanup(child)
        record_id = child.get('id')
        if record_id == 'sequence':
            child._value = int(child._value)
        return child

# TOOLS -----------------------------------------------

class Ref():
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"'{self.value}'"
    def __str__(self):
        return self.value

def indent(level=0, content="", indent_size=4):
    return f"{' ' * level * indent_size}{content}"

# -----------------------------------------------

def get_files(pattern, path=None):
    path = Path(path or Path.cwd())
    return glob.glob(str(path / pattern), recursive=True)

def parse_file(filename):
    tree = etree.parse(filename)
    root = tree.getroot()
    nodes_tree = []
    stack = [(nodes_tree, root)]
    parent = nodes_tree
    while stack:

        # Pop an element out of the stack
        parent, el = stack.pop(0)

        # Create a new node and attach it to the parent
        if el.tag == 'record':
            node = Record(el, el.tag)
            parent.append(node)
        elif el.tag == 'field':
            node = Field(el)
            parent.append(node)
        else:
            node = parent

        # Populate the stack with the node's children
        stack = [(node, child) for child in el] + stack

    return {record['id']: record for record in nodes_tree}

def merge_records(record_a, record_b):
    for _id, field in record_a['children'].items():
        record_b['children'][_id] = field

def get_records(module):
    records = {}
    for filename in get_files(f'addons/{module}/data/*.xml'):
        try:
            for key, value in parse_file(filename).items():
                # if the id is already present, merge the fields
                if key not in records:
                    records[key] = value
                else:
                    merge_records(value, records[key])
        except etree.ParseError as e:
            print(f"Invalid XML file {filename}, {e}")

    return records

# -----------------------------------------------------------

def split_template_from_company(all_records):
    company_record = ResCompany({'model': 'res.company'}, 'Record')
    company_fields = (
        'currency_id',
        'country_id',
        'account_fiscal_country_id',
        'default_pos_receivable_account_id',
        'account_default_pos_receivable_account_id',
        'income_currency_exchange_account_id',
        'expense_currency_exchange_account_id',
    )
    chart_templates = all_records.get('account.chart.template', {})
    for _record_id, record in chart_templates.items():
        for field_id, field in record.get('children', {}).items():
            if re.match('.*account_.*id.*', field_id):
                record['children'][field_id]._value = Unquoted(f"f'account.{{cid}}_{field._value}'")
        for field_id in company_fields:
            if field_id in record.get('children', {}):
                company_record.append(record['children'].pop(field_id))
    if company_record.get('children'):
        company_record['id'] = Unquoted("f'base.company_{cid}'")
        all_records['res.company'] = {company_record['id']: company_record}
    return all_records

def do_module(code, module, lang):
    """
        Translate an old Chart Template from a module to a new set of files and a Python class.
    """
    grouped_records = groupby(get_records(module).values(), lambda x: x['_model'])
    all_records = {model: {record['id']: record for record in records} for model, records in grouped_records}
    all_records["account.fiscal.position"] = convert_csv_to_records(module, "account_fiscal_position.csv", "account.fiscal.position", AccountFiscalPosition)
    all_records = split_template_from_company(all_records)

    # CSV files
    convert_old_csv(module, source="account.account.csv", destination="account.account.csv")
    convert_old_csv(module, source='account.group.csv', destination="account.group.csv")
    content = convert_records_to_csv(module, all_records, 'account.tax.group')
    if content:
        save_new_file(module, "account.tax.group.csv", content)
    else:
        convert_old_csv(module, source='account.tax.group.csv', destination="account.tax.group.csv")

    # XML files
    content = (
        "# -*- coding: utf-8 -*-\n"
        "# Part of Odoo. See LICENSE file for full copyright and licensing details.\n"
        "from odoo import models, Command, _\n"
        "from odoo.addons.account.models.chart_template import delegate_to_super_if_code_doesnt_match\n"
        "\n"
        "class AccountChartTemplate(models.AbstractModel):\n"
        "    _inherit = 'account.chart.template'\n"
        "    _template_code = '" + code + "'\n\n"
    ) + "\n".join([convert_records_to_function(module, all_records, model, function_name)
                   for model, function_name in (
                       ("account.chart.template", "_get_template_data"),
                       ("account.tax.template", "_get_account_tax"),
                       ("account.fiscal.position", "_get_fiscal_position"),
                       ("res.company", "_get_res_company"),
                   )])

    path = Path.cwd() / f'addons/{module}/models/account_chart_template.py'
    with open(str(path), 'w', encoding="utf-8") as outfile:
        outfile.write(content)

def convert_records_to_function(module, all_records, model, function_name, cid=True):
    """
        Convert a set of Records to a Python function.
    """
    records = all_records.get(model, {})
    stream = io.StringIO()
    stream.write(indent(1, "@delegate_to_super_if_code_doesnt_match\n") +
                 indent(1, f"def {function_name}(self, template_code, company):\n") +
                 (cid and indent(2, "cid = (company or self.env.company).id\n")) +
                 indent(2, "return "))
    if model == 'account.chart.template':
        for _id, record in records.items():
            stream.write(pformat(record, level=2).lstrip())
    else:
        stream.write("{\n")
        for i, (_id, record) in enumerate(records.items()):
            is_last = i >= len(records) - 1
            if model != 'res.company':
                key = Unquoted(f"f'{{cid}}_{record['id'].replace('.', '_')}'")
            else:
                key = record['id']
            value = pformat(record, level=3).strip()
            if not is_last:
                value += ','
            stream.write(indent(3, f"{key}: {value}\n"))
        stream.write(indent(2, "}\n"))
    return stream.getvalue()

def convert_csv_to_records(module, filename, model, cls):
    """
        Convert old CSV to Records, so that it can be further be processed.
        For example, it can be turned into a Python list.
    """
    lines = read_csv_lines(module, filename)
    records = {}
    if lines:
        header, *rows = lines
        header, rows = remove_chart_template_id(header, rows)
        for i, row in enumerate(rows):
            _id = f"{model}_{i}"
            records[_id] = cls({'id': _id, 'tag': cls.__name__, '_model': model}, model)
            for i, field_header in enumerate(header):
                is_ref = re.match(r'^ref\(.*\)$', row[i], re.I)
                records[_id].append(Field({
                    'id': field_header,
                    'text': row[i] if not is_ref else '',
                    'ref': Ref(row[i]) if is_ref else ''
                }))
    return records

# ---------------------------------------------------------

def cleanup_csv(header, rows):
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            if value in ('TRUE', 'FALSE'):
                rows[i][j] = {'TRUE': True, 'FALSE': False}.get(value)
    return header, rows

def remove_chart_template_id(header, rows):
    chart_template_id_col = None
    for i, field in enumerate(header):
        if field in ('chart_template_id/id', 'chart_template_id:id'):
            chart_template_id_col = i
        elif field.endswith(':id') or field.endswith('/id'):
            header[i] = header[i][:-3]
    if chart_template_id_col:
        header.pop(chart_template_id_col)
        for row in rows:
            row.pop(chart_template_id_col)
    return header, rows

def convert_records_to_csv(module, all_records, model):
    records = all_records.get(model, {})
    header, rows = [], []
    for i, (_id, record) in enumerate(records.items()):
        if i == 0:
            for _id in record.get('children', {}):
                header.append(_id.replace(":", "/"))
        rows.append([field._value for _id, field in record.get('children', {}).items()])
    return generate_csv_content(header, rows)

def generate_csv_content(header, rows):
    if not header or not rows:
        return None
    fields_per_rows = [','.join([str(field) for field in row]) for row in rows]
    return (','.join(header) + '\n' + '\n'.join(fields_per_rows)).strip()

def read_csv_lines(module, filename):
    csvfile = (load_old_source(module, filename) or '').split('\n')
    if not csvfile:
        return []
    reader = csv.reader(csvfile, delimiter=',')
    return [line for line in reader if line]

def convert_old_csv(module, source, destination, callback=None):
    lines = read_csv_lines(module, filename=source)
    if lines:
        header, *rows = lines
        header, rows = remove_chart_template_id(header, rows)
        header, rows = cleanup_csv(header, rows)
        if callback:
            header, rows = callback(header, rows)
        content = generate_csv_content(header, rows)
        save_new_file(module, destination, content)

def load_old_source(module, filename):
    """
        Look for old Chart Template file and read it.
    """
    stem, suffix = Path(filename).stem, Path(filename).suffix
    filenames = (
        filename,
        filename.replace('_', '.'),
        f"{stem}_template{suffix}",
        (f"{stem}_template{suffix}").replace('_', '.'),
    )
    for name in filenames:
        path = Path.cwd() / f'addons/{module}/data/{name}'
        if path.exists():
            break
    else:
        print(f"Cannot find {filename} file for {module}")
        return

    with open(path, newline='', encoding='utf-8') as infile:
        return infile.read()

def save_new_file(module, filename, content):
    path = Path.cwd() / f'addons/{module}/data/template'
    if not path.is_dir():
        path.mkdir()
    with open(str(path / filename), 'w', encoding="utf-8") as outfile:
        outfile.write(content)

# -----------------------------------------------------------

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("usage: transform_coa.py <code> <module> <lang>\n"
              "Example: transform_coa.py it l10n_it it_IT")
        sys.exit(1)
    do_module(sys.argv[1], sys.argv[2], sys.argv[3])
