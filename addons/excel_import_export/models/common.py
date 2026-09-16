# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import csv
import itertools
import re
import string
import uuid
from ast import literal_eval
from datetime import datetime as dt
from io import StringIO

import xlrd
from dateutil.parser import parse

from odoo import _
from odoo.exceptions import ValidationError


def adjust_cell_formula(value, k):
    """Cell formula, i.e., if i=5, val=?(A11)+?(B12) -> val=A16+B17"""
    if isinstance(value, str):
        for i in range(value.count("?(")):
            if value and "?(" in value and ")" in value:
                i = value.index("?(")
                j = value.index(")", i)
                val = value[i + 2 : j]
                col, row = split_row_col(val)
                new_val = "{}{}".format(col, row + k)
                value = value.replace("?(%s)" % val, new_val)
    return value


def get_field_aggregation(field):
    """i..e, 'field@{sum}'"""
    if field and "@{" in field and "}" in field:
        i = field.index("@{")
        j = field.index("}", i)
        cond = field[i + 2 : j]
        try:
            if cond or cond == "":
                return (field[:i], cond)
        except Exception:
            return (field.replace("@{%s}" % cond, ""), False)
    return (field, False)


def get_field_condition(field):
    """i..e, 'field${value > 0 and value or False}'"""
    if field and "${" in field and "}" in field:
        i = field.index("${")
        j = field.index("}", i)
        cond = field[i + 2 : j]
        try:
            if cond or cond == "":
                return (field.replace("${%s}" % cond, ""), cond)
        except Exception:
            return (field, False)
    return (field, False)


def get_field_style(field):
    """
    Available styles
    - font = bold, bold_red
    - fill = red, blue, yellow, green, grey
    - align = left, center, right
    - number = true, false
    i.e., 'field#{font=bold;fill=red;align=center;style=number}'
    """
    if field and "#{" in field and "}" in field:
        i = field.index("#{")
        j = field.index("}", i)
        cond = field[i + 2 : j]
        try:
            if cond or cond == "":
                return (field.replace("#{%s}" % cond, ""), cond)
        except Exception:
            return (field, False)
    return (field, False)


def get_field_style_cond(field):
    """i..e, 'field#?object.partner_id and #{font=bold} or #{}?'"""
    if field and "#?" in field and "?" in field:
        i = field.index("#?")
        j = field.index("?", i + 2)
        cond = field[i + 2 : j]
        try:
            if cond or cond == "":
                return (field.replace("#?%s?" % cond, ""), cond)
        except Exception:
            return (field, False)
    return (field, False)


def fill_cell_style(field, field_style, styles):
    field_styles = field_style.split(";") if field_style else []
    for f in field_styles:
        (key, value) = f.split("=")
        if key not in styles.keys():
            raise ValidationError(_("Invalid style type %s") % key)
        if value.lower() not in styles[key].keys():
            raise ValidationError(
                _("Invalid value %(value)s for style type %(key)s")
                % {"value": value, "key": key}
            )
        cell_style = styles[key][value]
        if key == "font":
            field.font = cell_style
        if key == "fill":
            field.fill = cell_style
        if key == "align":
            field.alignment = cell_style
        if key == "style":
            if value == "text":
                try:
                    # In case value can't be encoded as utf, we do normal str()
                    field.value = field.value.encode("utf-8")
                except Exception:
                    field.value = str(field.value)
            field.number_format = cell_style


def get_line_max(line_field):
    """i.e., line_field = line_ids[100], max = 100 else 0"""
    if line_field and "[" in line_field and "]" in line_field:
        i = line_field.index("[")
        j = line_field.index("]")
        max_str = line_field[i + 1 : j]
        try:
            if len(max_str) > 0:
                return (line_field[:i], int(max_str))
            else:
                return (line_field, False)
        except Exception:
            return (line_field, False)
    return (line_field, False)


def get_groupby(line_field):
    """i.e., line_field = line_ids["a_id, b_id"], groupby = ["a_id", "b_id"]"""
    if line_field and "[" in line_field and "]" in line_field:
        i = line_field.index("[")
        j = line_field.index("]")
        groupby = literal_eval(line_field[i : j + 1])
        return groupby
    return False


def split_row_col(pos):
    match = re.match(r"([a-z]+)([0-9]+)", pos, re.I)
    if not match:
        raise ValidationError(_("Position %s is not valid") % pos)
    col, row = match.groups()
    return col, int(row)


def openpyxl_get_sheet_by_name(book, name):
    """Get sheet by name for openpyxl"""
    i = 0
    for sheetname in book.sheetnames:
        if sheetname == name:
            return book.worksheets[i]
        i += 1
    raise ValidationError(_("'%s' sheet not found") % (name,))


def xlrd_get_sheet_by_name(book, name):
    try:
        for idx in itertools.count():
            sheet = book.sheet_by_index(idx)
            if sheet.name == name:
                return sheet
    except IndexError as exc:
        raise ValidationError(_("'%s' sheet not found") % (name,)) from exc


def isfloat(input_val):
    try:
        float(input_val)
        return True
    except ValueError:
        return False


def isinteger(input_val):
    try:
        int(input_val)
        return True
    except ValueError:
        return False


def isdatetime(input_val):
    try:
        if len(input_val) == 10:
            dt.strptime(input_val, "%Y-%m-%d")
        elif len(input_val) == 19:
            dt.strptime(input_val, "%Y-%m-%d %H:%M:%S")
        else:
            return False
        return True
    except ValueError:
        return False


def str_to_number(input_val):
    if isinstance(input_val, str):
        if " " not in input_val:
            if isdatetime(input_val):
                return parse(input_val)
            elif isinteger(input_val):
                if not (len(input_val) > 1 and input_val[:1] == "0"):
                    return int(input_val)
            elif isfloat(input_val):
                if not (input_val.find(".") > 2 and input_val[:1] == "0"):
                    return float(input_val)
    return input_val


def csv_from_excel(excel_content, delimiter, quote):
    wb = xlrd.open_workbook(file_contents=excel_content)
    sh = wb.sheet_by_index(0)
    content = StringIO()
    quoting = csv.QUOTE_ALL
    if not quote:
        quoting = csv.QUOTE_NONE
    if delimiter == " " and quoting == csv.QUOTE_NONE:
        quoting = csv.QUOTE_MINIMAL
    wr = csv.writer(content, delimiter=delimiter, quoting=quoting)
    for rownum in range(sh.nrows):
        row = []
        for x in sh.row_values(rownum):
            if quoting == csv.QUOTE_NONE and delimiter in x:
                raise ValidationError(
                    _(
                        "Template with CSV Quoting = False, data must not "
                        'contain the same char as delimiter -> "%s"'
                    )
                    % delimiter
                )
            row.append(x)
        wr.writerow(row)
    content.seek(0)  # Set index to 0, and start reading
    out_file = content.getvalue().encode("utf-8")
    return out_file


def pos2idx(pos):
    match = re.match(r"([a-z]+)([0-9]+)", pos, re.I)
    if not match:
        raise ValidationError(_("Position %s is not valid") % (pos,))
    col, row = match.groups()
    col_num = 0
    for c in col:
        if c in string.ascii_letters:
            col_num = col_num * 26 + (ord(c.upper()) - ord("A")) + 1
    return (int(row) - 1, col_num - 1)


def _get_cell_value(cell, field_type=False):
    """If Odoo's field type is known, convert to valid string for import,
    if not know, just get value  as is"""
    value = False
    datemode = 0  # From book.datemode, but we fix it for simplicity
    if field_type in ["date", "datetime"]:
        ctype = xlrd.sheet.ctype_text.get(cell.ctype, "unknown type")
        if ctype in ("xldate", "number"):
            is_datetime = cell.value % 1 != 0.0
            time_tuple = xlrd.xldate_as_tuple(cell.value, datemode)
            date = dt(*time_tuple)
            value = (
                date.strftime("%Y-%m-%d %H:%M:%S")
                if is_datetime
                else date.strftime("%Y-%m-%d")
            )
        else:
            value = cell.value
    elif field_type in ["integer", "float"]:
        value_str = str(cell.value).strip().replace(",", "")
        if len(value_str) == 0:
            value = ""
        elif value_str.replace(".", "", 1).isdigit():  # Is number
            if field_type == "integer":
                value = int(float(value_str))
            elif field_type == "float":
                value = float(value_str)
        else:  # Is string, no conversion
            value = value_str
    elif field_type in ["many2one"]:
        # If number, change to string
        if isinstance(cell.value, (int, float, complex)):
            value = str(cell.value)
        else:
            value = cell.value
    else:  # text, char
        value = cell.value
    # If string, cleanup
    if isinstance(value, str):
        if value[-2:] == ".0":
            value = value[:-2]
    # Except boolean, when no value, we should return as ''
    if field_type not in ["boolean"]:
        if not value:
            value = ""
    return value


def _add_column(column_name, column_value, file_txt):
    i = 0
    txt_lines = []
    for line in file_txt.split("\n"):
        if line and i == 0:
            line = '"' + str(column_name) + '",' + line
        elif line:
            line = '"' + str(column_value) + '",' + line
        txt_lines.append(line)
        i += 1
    file_txt = "\n".join(txt_lines)
    return file_txt


def _add_id_column(file_txt):
    i = 0
    txt_lines = []
    for line in file_txt.split("\n"):
        if line and i == 0:
            line = '"id",' + line
        elif line:
            line = f"__excel_import_export__.{uuid.uuid4()},{line}"
        txt_lines.append(line)
        i += 1
    file_txt = "\n".join(txt_lines)
    return file_txt
