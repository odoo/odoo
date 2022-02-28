#!/usr/bin/env python3

import glob
import sys
import csv
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

    def pprint(self, level=0, stream=None):
        stream = stream or sys.stdout
        for child in self.get('children', []):
            child.pprint(level + 1, stream)

class Field(Node):
    def __init__(self, el):
        super().__init__(el)
        text = (el.text or '').strip()
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

class ResCompany(Record):
    _from = 'account.chart.template'

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

def do_module(module, lang):
    convert_account_account_csv(module, )
    convert_account_group_csv(module)
    convert_account_tax_group_xml(module)

def convert_account_tax_group_xml(module):
    records = {id: record for id, record in get_records(module).items()
               if record['_model'] == 'account.tax.group'}
    header = ['name', 'country_id/id']
    rows = []
    for _id, record in records.items():
        rows.append([field._value for _id, field in record['children'].items()])
    content = generate_csv(header, rows)
    save_file(module, "account.tax.group.csv", content)

def generate_csv(header, rows):
    fields_per_rows = [','.join([str(field) for field in row]) for row in rows]
    return ','.join(header) + '\n' + '\n'.join(fields_per_rows)

def convert_account_account_csv(module, lang):
    header, rows = load_csv(module, filename='account_account_template.csv')
    header, rows = remove_chart_template_id(header, rows)
    header.append(f"name@{lang}")
    content = ','.join(header) + '\n' + '\n'.join([','.join(row) for row in rows])
    save_file(module, "account.account.csv", content)

def convert_account_group_csv(module):
    header, rows = load_csv(module, filename='account_group_template.csv')
    header, rows = remove_chart_template_id(header, rows)
    content = ','.join(header) + '\n' + '\n'.join([','.join(row) for row in rows])
    save_file(module, "account.group.csv", content)

def remove_chart_template_id(header, rows):
    chart_template_id_col = header.index('chart_template_id/id')
    if chart_template_id_col:
        header.pop(chart_template_id_col)
        for row in rows:
            row.pop(chart_template_id_col)
    return header, rows

def load_csv(module, filename):
    csvfile = load_file(module, filename).split('\n')
    reader = csv.reader(csvfile, delimiter=',')
    header, *rows = [line for line in reader if line]
    return header, rows

def load_file(module, filename):
    filenames = (filename,
                 filename.replace('_', '.'),
                 filename[:-4] + '_template.csv',
                 (filename[:-4] + '_template.csv').replace('_', '.'))
    for name in filenames:
        path = Path.cwd() / f'addons/{module}/data/{name}'
        if path.exists():
            break
    else:
        raise ValueError(f"Cannot find account_account file for {module}")

    with open(path, newline='', encoding='utf-8') as infile:
        return infile.read()

def save_file(module, filename, content):
    path = Path.cwd() / f'addons/{module}/data/template'
    if not path.is_dir():
        path.mkdir()
    with open(str(path / filename), 'w', encoding="utf-8") as outfile:
        outfile.write(content)

def get_records(module):
    records = {}
    for filename in get_files(f'addons/{module}/data/*.xml'):
        try:
            records.update(run_file(filename))
        except etree.ParseError as e:
            print(f"Invalid XML file {filename}, {e}")

    return records

if __name__ == '__main__':
    do_l10n_fr()
    # elif command == 'eval':
    #     record_id = 'account_fr_tag_salaires'
    #     record = records.get(record_id)
    #     if not record:
    #         sys.exit(1)

    #     stream = io.StringIO()
    #     record.pprint(stream=stream)
    #     eval_record = safe_eval(stream.getvalue(), globals_dict={
    #         "ref": env.ref,
    #         "Command": Command
    #     })

    #     model = record['_model']
    #     added_record = env[model]._load_records([{'values': eval_record}])
    #     print(added_record)
