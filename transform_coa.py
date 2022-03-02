#!/usr/bin/env python3

import glob
import io
import sys
import csv
from itertools import groupby
from pathlib import Path
from pprint import pformat

from lxml import etree

from odoo import Command
from odoo.tools.safe_eval import safe_eval

self = locals().get('self') or {}
env = locals().get('env') or {}

# Classes -----------------------------------------------

class Node(dict):
    def __init__(self, el):
        super().__init__({'id': el.get('id', el.get('name'))})

    def append(self, child):
        children = self.get('children') or []
        children.append(child)
        self['children'] = children

    def pformat(self, level=0):
        stream = io.StringIO()
        self.pprint(level, stream)
        return stream.getvalue()

    def pprint(self, level=0, stream=None):
        stream = stream or sys.stdout
        for child in self.get('children', []):
            child.pprint(level + 1, stream)

class Field(Node):
    def __init__(self, el):
        super().__init__(el)
        text = (el.get('text') or (hasattr(el, 'text') and el.text) or '').strip()
        ref = el.get('ref', '').strip()
        _eval = el.get('eval', '').strip()
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

    def pprint(self, level=0, stream=None):
        stream = stream or sys.stdout
        if self.value_type:
            if isinstance(self._value, (tuple, list, dict)):
                lines = pformat(self._value).split('\n')
                value_str = ''.join([f"\n{indent(level+1)}{line}" for line in lines])
            else:
                value_str = repr(self._value)
            stream.write(f"{indent(level)}{repr(self['id'])}: {value_str},\n")
        elif self.get('children'):
            stream.write(f"{indent(level)}{repr(self['id'])}: [\n")
            stream.write(f"{indent(level + 1)}Command.clear(),\n")
            for child in self.get('children', []):
                stream.write(f"{indent(level + 1)}Command.create(")
                child.pprint(level+1, stream, start_indent=False)
                stream.write("),\n")
            stream.write(f"{indent(level)}]\n")

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
        if isinstance(value, str) and value in ('True', 'False', 'None'):
            child._value = safe_eval(child._value)
        elif record_id == 'sequence':
            child._value = int(child._value)
        elif record_id == 'amount':
            child._value = float(child._value)
        return child

    def pprint(self, level=0, stream=None, start_indent=True):
        stream = stream or sys.stdout
        stream.write(f"{indent(level) if start_indent else ''}{{\n")
        for key, value in self['children'].items():
            if isinstance(value, Field):
                value.pprint(level+1, stream)
            else:
                stream.write(f"{indent(level)}{' ' * 4}{repr(key)}: {repr(value)},\n")
        stream.write(f"{indent(level)}}}" + ('\n' if start_indent else ''))

    def cleanup_o2m(self, child):
        value = child._value
        if isinstance(value, (tuple, list)):
            for i, sub in enumerate(value):
                if list(sub) == [5, 0, 0]:
                    value[i] = Unquoted("Command.clear()")
                elif (isinstance(sub, (list, tuple)) and
                      len(sub) == 3 and
                      sub[0] == Command.CREATE and
                      sub[1] == 0 and
                      isinstance(sub[2], dict)):
                    value[i] = Unquoted(f"Command.create({repr(sub[2])})")
                elif (isinstance(sub, (list, tuple)) and
                      len(sub) == 3 and
                      sub[0] == Command.SET and
                      sub[1] == 0 and
                      isinstance(sub[2], list)):
                    value[i] = Unquoted(f"Command.set({repr(sub[2])})")
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
        elif record_id in ('invoice_repartition_line_ids', 'refund_repartition_line_ids'):
            child._value = self.cleanup_o2m(child)
        return child

class AccountTaxRepartitionLine(Record):
    _from = 'account.tax.repartition.line'

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

# -----------------------------------------------

class Ref():
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"ref('{self.value}')"
    def __str__(self):
        return self.value

def get_files(pattern, path=None):
    path = Path(path or Path.cwd())
    return glob.glob(str(path / pattern), recursive=True)

def indent(level=0, indent_size=4):
    return ' ' * level * indent_size

def run_file(filename):
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
            for key, value in run_file(filename).items():
                # if the id is already present, merge the fields
                if key not in records:
                    records[key] = value
                else:
                    merge_records(value, records[key])
        except etree.ParseError as e:
            print(f"Invalid XML file {filename}, {e}")

    return records

# -----------------------------------------------------------

def do_module(module, lang):
    all_records = {model: list(records) for model, records in groupby(get_records(module), lambda x: x['_model'])}

    convert_old_csv(module, source="account_account_template.csv", destination="account.account.csv",
                    callback=lambda header, rows: header.append(f"name@{lang}") or (header, rows))
    convert_old_csv(module, source='account_group_template.csv', destination="account.group.csv")
    content = convert_records_to_csv(module, all_records['account.tax.group'], 'account.tax.group')
    save_new_file(module, "account.tax.group.csv", content)

    content = convert_records_to_function(module, all_records['account.chart.template'], "account.chart.template", "_get_template_data")
    content = convert_records_to_function(module, all_records['account.tax.template'], "account.tax.template", "_get_account_tax")
    content += "\n" + convert_account_fiscal_position_template_csv(module)
    save_new_file(module, "chart_template.py", content)

def convert_records_to_function(module, records, model, function_name, cid=True):
    stream = io.StringIO()
    cid_str = cid and f"{indent(2)}(company or self.env.company).id"
    stream.write(f"{indent(1)}@delegate_to_super_if_code_doesnt_match\n"
                 f"{indent(1)}def {function_name}(self, template_code, company):\n" +
                 cid_str +
                 f"{indent(2)}return ")
    if len(records) == 1:
        for _id, record in records.items():
            stream.write(record.pformat(2).lstrip())
    else:
        stream.write("[\n")
        for i, (_id, record) in enumerate(records.items()):
            is_last = i < len(records) - 1
            stream.write(record.pformat(3).rstrip() + (is_last and "" or ",") + "\n")
        stream.write("{indent(2)}]\n")
    return stream.getvalue()

def convert_account_fiscal_position_template_csv(module):
    lines = read_csv_lines(module, filename='account_fiscal_position.csv')
    records = {}
    if lines:
        header, *rows = lines
        header, rows = remove_chart_template_id(header, rows)
        for row in rows:
            _id = f"account_fiscal_position_{id}"
            records[_id] = AccountFiscalPosition({
                'id': _id,
                'tag': 'AccountFiscalPosition',
                '_model': 'account.fiscal.position'
            }, 'account.fiscal.position')
            for i, field_header in enumerate(header):
                is_ref = row[i].startswith('ref(')
                records[_id].append(Field({
                    'id': field_header,
                    'text': row[i] if not is_ref else '',
                    'ref': Ref(row[i]) if is_ref else ''
                }))
    return convert_records_to_function(module, records, "account.fiscal.position", "_get_fiscal_position", cid=True)

# ---------------------------------------------------------

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

def convert_records_to_csv(module, records, model):
    header, rows = [], []
    for i, (_id, record) in enumerate(records.items()):
        if i == 0:
            for _id in record.get('children', {}):
                header.append(_id.replace(":", "/"))
        rows.append([field._value for _id, field in record.get('children', {}).items()])
    return generate_csv_content(header, rows)

def generate_csv_content(header, rows):
    fields_per_rows = [','.join([str(field) for field in row]) for row in rows]
    return ','.join(header) + '\n' + '\n'.join(fields_per_rows)

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
        if callback:
            header, rows = callback(header, rows)
        content = generate_csv_content(header, rows)
        save_new_file(module, destination, content)

def load_old_source(module, filename):
    stem, suffix = Path(filename).stem, Path(filename).suffix
    filenames = (filename,
                 filename.replace('_', '.'),
                 f"{stem}_template{suffix}",
                 (f"{stem}_template{suffix}").replace('_', '.'))
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
    # do_module("l10n_fr", "fr_FR")
    do_module("l10n_it", "it_IT")
