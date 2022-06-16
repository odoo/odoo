#!/usr/bin/env python3

import glob
import io
import sys
import csv
import re
import logging
from pathlib import Path

from lxml import etree

from odoo import Command
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

self = locals().get('self') or {}
env = locals().get('env') or {}


def get_command(x):
    return ['create', 'update', 'delete', 'unlink', 'link', 'clear', 'set'][x]


def pformat(item, level=0, stream=None):

    def pformat_field_record(value, stream):
        stream.write(pformat(value.get('children', {}), level=level))

    def pformat_tuple_list(value, stream):
        start, end = '[]' if isinstance(value, list) else '()'
        stream.write(indent(level, start + '\n'))
        is_o2m = all([isinstance(sub, (tuple, list))
                      and len(sub) in (2, 3)
                      and all([isinstance(x, int) for x in sub[:2]])
                      for sub in value])
        for i, subitem in enumerate(value):
            if is_o2m:
                subitem = list(subitem)
                if subitem == [5, 0, 0]:
                    value_str = Unquoted("Command.clear()")
                elif len(subitem) == 3:
                    subvalue_str = pformat(subitem[2], level+1).strip()
                    name = get_command(subitem[0])
                    value_str = Unquoted(f"Command.{name}({subvalue_str})")
            else:
                value_str = repr(subitem)
            comma = ',' if i < len(value) else ''
            stream.write(indent(level + 1, f"{value_str}{comma}\n"))
        stream.write(indent(level, end))

    def pformat_dict(value, stream):
        stream.write(indent(level, '{\n'))
        for i, (key, subitem) in enumerate(value.items()):
            if isinstance(subitem, Field):
                subvalue = subitem._value
            else:
                subvalue = subitem
            value_str = pformat(subvalue, level + 1).lstrip()
            comma = ',' if i < len(value) else ''
            stream.write(indent(level + 1, f"{repr(key)}: {value_str}{comma}\n"))
        stream.write(indent(level, '}\n'))

    stream = stream or io.StringIO()
    mapping = [
        ((Field, Record), pformat_field_record),
        ((tuple, list), pformat_tuple_list),
        ((dict,), pformat_dict)
    ]
    for types, formatter in mapping:
        if isinstance(item, types):
            formatter(item, stream)
            break
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
        unquoted = el.get('unquoted', '')
        if unquoted:
            text = Unquoted(text)
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
        def get_all_subclasses(cls):
            subclass_list = []
            def recurse(klass):
                for subclass in klass.__subclasses__():
                    subclass_list.append(subclass)
                    recurse(subclass)
            recurse(cls)
            return subclass_list
        subclasses = get_all_subclasses(Record)
        mapping = {cls._from: cls for cls in subclasses if cls._from}
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
        elif record_id == 'chart_template_id':
            child['delete'] = True
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

def unquote_ref(value):
    return Unquoted(f"f'account.{{cid}}_{value}'")

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
        if record_id in ('name', 'currency_id'):
            child['delete'] = True
        return child

class AccountReconcileModel(Record):
    _from = 'account.reconcile.model'

class AccountReconcileModelLine(Record):
    _from = 'account.reconcile.model.line'

class ResCompany(Record):
    _from = 'res.company'

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
        if record_id == 'tax_group_id':
            child._value = unquote_ref(child._value)
        elif record_id in ('invoice_repartition_line_ids', 'refund_repartition_line_ids'):
            child._value = self.cleanup_o2m(child, AccountTaxRepartitionLine)
        elif record_id == 'price_include':
            child._value = bool(child._value)
        return child

    def get_repartition_lines(self):
        for name, child in self['children'].items():
            if name in ('invoice_repartition_line_ids', 'refund_repartition_line_ids'):
                yield child._value

class AccountTaxRepartitionLine(Record):
    _from = 'account.tax.repartition.line'
    def cleanup(self, child):
        child = super().cleanup(child)
        record_id = child.get('id')
        if record_id == 'account_id':
            child._value = unquote_ref(child._value)
        elif record_id in ('plus_report_line_ids', 'minus_report_line_ids'):
            values = [f"'{x}'" for x in child._value]
            child._value = Unquoted(f"tags({', '.join(values)})")
        return child

    def cleanup_tags(self, tags):
        tokens = []
        to_be_removed = []
        for name, child in self.get('children', {}).items():
            if name in ('plus_report_line_ids', 'minus_report_line_ids'):
                sign = '+' if name == 'plus_report_line_ids' else '-'
                tokens += [f"'{sign}{tags[x]}'" for x in re.findall("'([^']+)'", child._value)]
                to_be_removed.append(name)
        for name in to_be_removed:
            del self['children'][name]
        if tokens:
            self['children']['tag_ids'] = Field({'id': 'tag_ids', 'text': "tags(" + ", ".join(tokens) + ")", 'unquoted': True})

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

class AccountFiscalPositionTemplate(AccountFiscalPosition):
    _from = 'account.fiscal.position.template'

class AccountFiscalPositionTaxTemplate(Record):
    _from = 'account.fiscal.position.tax.template'
    def cleanup(self, child):
        child = super().cleanup(child)
        record_id = child.get('id')
        if record_id in ('position_id', 'tax_src_id', 'tax_dest_id'):
            child._value = unquote_ref(child._value)
        return child

class AccountFiscalPositionAccountTemplate(Record):
    _from = 'account.fiscal.position.account.template'
    def cleanup(self, child):
        child = super().cleanup(child)
        record_id = child.get('id')
        if record_id in ('position_id', 'account_src_id', 'account_dest_id'):
            child._value = unquote_ref(child._value)
        return child

class AccountTaxReport(Record):
    _from = 'account.tax.report'
    def cleanup(self, child):
        child = super().cleanup(child)
        record_id = child.get('id')
        if record_id == 'root_line_ids':
            child._value = self.cleanup_o2m(child)
        return child

    def get_lines(self):
        for name, child in self['children'].items():
            if name == 'root_line_ids':
                yield from child['children']
                break

    def get_tags(self):
        tags = {}
        for line in self.get_lines():
            tags.update(line.get_tags())
        return tags

class AccountTaxReportLine(Record):
    _from = 'account.tax.report.line'
    def cleanup(self, child):
        child = super().cleanup(child)
        record_id = child.get('id')
        if record_id == 'sequence':
            child._value = int(child._value)
        return child

    def get_lines(self):
        for name, child in self.get('children', {}).items():
            if name == 'children_line_ids':
                yield from child['children']
                break

    def get_tag_name(self):
        for name, child in self.get('children', {}).items():
            if name == 'tag_name':
                return child._value

    def get_tags(self):
        tags = {}
        tag = self.get_tag_name()
        if tag:
            tags[self['id']] = tag
        for line in self.get_lines():
            subtags = line.get_tags()
            tags.update(subtags)
        return tags

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
        if el.tag in ('record', 'function'):
            node = Record(el, el.tag)
            node._filename = filename
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
            _logger.warning("Invalid XML file %s, %s", filename, e)
    return records

# -----------------------------------------------------------

def split_template_from_company(all_records):
    company_record = ResCompany({'model': 'res.company'}, 'Record')
    company_fields = (
        'country_id',
        'default_pos_receivable_account_id',
        'account_default_pos_receivable_account_id',
        'income_currency_exchange_account_id',
        'expense_currency_exchange_account_id',
    )
    chart_templates = all_records.get('account.chart.template', {})
    for _record_id, record in chart_templates.items():
        for field_id, field in record.get('children', {}).items():
            if re.match('.*account_.*id.*', field_id):
                record['children'][field_id]._value = unquote_ref(field._value)
        for field_id in company_fields:
            if field_id in record.get('children', {}):
                child = record['children'].pop(field_id)
                # Convert the account_fiscal_country_id which was still named country_id in the ACT
                if field_id == 'country_id':
                    child['id'] = 'account_fiscal_country_id'
                company_record.append(child)
    if company_record.get('children'):
        company_record['id'] = Unquoted("company.get_external_id()[cid]")
        all_records['res.company'] = {company_record['id']: company_record}
    return all_records

def convert_try_loading(country_code, all_records):
    try_loading = next((v for k, v in all_records['account.chart.template'].items() if v['tag'] == 'function'), None)
    if try_loading:
        with open(try_loading._filename, "a", encoding="utf-8") as f:
            f.write(
f"""<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <function model="account.chart.template" name="try_loading">
            <value eval="[]"/>
            <value>{country_code}</value>
            <value eval="None"/>
        </function>
    </data>
</odoo>""")

def get_tags(records):
    return {k: v for report in records for k, v in report.get_tags().items()}

def cleanup_tax_tags(all_records):
    tags = get_tags(all_records.get('account.tax.report', {}).values())
    taxes = all_records.get('account.tax.template', {}).values()
    many_fields = [line for x in taxes for lines in x.get_repartition_lines() for line in lines]
    for token in many_fields:
        if len(token) == 3 and token[0] == 0:
            token[2].cleanup_tags(tags)

def do_module(code, module, lang):
    """
        Translate an old Chart Template from a module to a new set of files and a Python class.
    """
    all_records = {}
    for value in get_records(module).values():
        model, _id = value['_model'], value['id']
        if model not in all_records:
            all_records[model] = {}
        all_records[model][_id] = value
    all_records["account.fiscal.position"] = convert_csv_to_records(module, "account_fiscal_position.csv", "account.fiscal.position", AccountFiscalPosition)
    all_records = split_template_from_company(all_records)

    # CSV files
    def add_translation_header(header, rows):
        header.append(f'"name@{lang}"')
        return header, rows
    convert_old_csv(module, source="account.account.csv", destination="account.account.csv", callback=add_translation_header)
    convert_old_csv(module, source='account.group.csv', destination="account.group.csv")
    content = convert_records_to_csv(module, all_records, 'account.tax.group')
    if content:
        save_new_file(module, "account.tax.group.csv", content)
    else:
        convert_old_csv(module, source='account.tax.group.csv', destination="account.tax.group.csv")
    convert_try_loading(lang[-2:].lower(), all_records)

    cleanup_tax_tags(all_records)

    # XML files
    contents = {}
    mapping = {
        "account.chart.template":           f"_get_{code}_template_data",
        "account.tax":                      f"_get_{code}_account_tax",
        "res.company":                      f"_get_{code}_res_company",
        "account.fiscal.position":          f"_get_{code}_fiscal_position",
        "account.reconcile.model":          f"_get_{code}_reconcile_model",
        "account.reconcile.model.line":     f"_get_{code}_reconcile_model_line",
        "account.fiscal.position.tax":      f"_get_{code}_fiscal_position_tax",
        "account.fiscal.position.account":  f"_get_{code}_fiscal_position_account",
    }
    extra_functions = []
    for model, function_name in mapping.items():
        for model_name in (model, model + '.template'):
            one_level = model_name == 'account.chart.template'
            set_company = model_name == 'res.company'
            content = convert_records_to_function(
                all_records,
                model_name,
                function_name,
                set_company=set_company,
                one_level=one_level)
            if content:
                contents[function_name] = contents.get(function_name, "") + content
                if model not in ("account.chart.template", "account.tax", "res.company"):
                    extra_functions.append((model, function_name))

    content = (
        "# -*- coding: utf-8 -*-\n"
        "# Part of Odoo. See LICENSE file for full copyright and licensing details.\n"
        "from odoo import models, Command\n"
        "\n"
        "class AccountChartTemplate(models.AbstractModel):\n"
        "    _inherit = 'account.chart.template'\n\n"
    )

    if extra_functions:
        content += (
            f"    def _get_{code}_chart_template_data(self, template_code, company):\n"
             "        return {\n"
             "            **self._get_chart_template_data(template_code, company),\n"
        )
        for model, function_name in extra_functions:
            content += f"            '{model}': self.{function_name}(template_code, company),\n"
        content += "        }\n"

    if contents:
        content += "\n".join(contents.values())

    path = Path.cwd() / f'addons/{module}/models/account_chart_template.py'
    with open(str(path), 'w', encoding="utf-8") as outfile:
        outfile.write(content)

def convert_records_to_function(all_records, model, function_name, set_company=False, one_level=False):
    """
        Convert a set of Records to a Python function.
    """
    records = all_records.get(model, {})
    if not records:
        return ''

    stream = io.StringIO()
    stream.write(indent(1, f"def {function_name}(self, template_code, company):\n") +
                 (set_company and indent(2, "company = (company or self.env.company)\n") or '') +
                 indent(2, "cid = (company or self.env.company).id\n") +
                 (model == 'account.tax.template' and indent(2, "tags = self._get_tag_mapper(template_code)\n") or '') +
                 indent(2, "return "))

    if one_level:
        record = None
        stream.write(pformat(list(records.items())[0][1], level=2).lstrip())
        return stream.getvalue()

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
        header, rows = remove_column(header, rows, ('chart_template_id/id', 'chart_template_id:id'))
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
    for i, column in enumerate(header):
        if column in ('user_type_id', 'tag_ids', 'country_id'):
            column = column + '/id'
        header[i] = '"' + str(column).replace('"', '\\"') + '"'
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            if value in ('TRUE', 'FALSE'):
                rows[i][j] = {'TRUE': True, 'FALSE': False}.get(value)
            rows[i][j] = '"' + str(value).replace('"', '\\"') + '"'
    return header, rows

def remove_column(header, rows, fields):
    column = None
    for i, field in enumerate(header):
        if field in fields:
            column = i
        elif field.endswith(':id') or field.endswith('/id'):
            header[i] = header[i][:-3]
    if column:
        header.pop(column)
        for row in rows:
            row.pop(column)
    return header, rows

def convert_records_to_csv(module, all_records, model):
    records = all_records.get(model, {})
    header, rows = [], []
    added_id = False
    for i, (_id, record) in enumerate(records.items()):
        children = record.get('children', {})
        if i == 0:
            for _id in children:
                header.append(_id.replace(":", "/"))
            if 'id' not in header:
                added_id = True
                header.insert(0, "id")
        rows.append([record['id'] if added_id else []] + [field._value for field in children.values()])
    header, rows = cleanup_csv(header, rows)
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
        header, rows = remove_column(header, rows, ('chart_template_id/id', 'chart_template_id:id'))
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
        _logger.warning("Cannot find %s file for %s", filename, module)
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
        _logger.warning("usage: transform_coa.py <code> <module> <lang>\n"
                     "Example: transform_coa.py it l10n_it it_IT")
        sys.exit(1)
    do_module(sys.argv[1], sys.argv[2], sys.argv[3])
