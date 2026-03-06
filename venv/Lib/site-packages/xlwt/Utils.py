# see the xlwt.license module for details of licensing.

# Utilities for work with reference to cells and with sheetnames

import re
from .ExcelMagic import MAX_ROW, MAX_COL
from .compat import xrange

_re_cell_ex = re.compile(r"(\$?)([A-I]?[A-Z])(\$?)(\d+)", re.IGNORECASE)
_re_row_range = re.compile(r"\$?(\d+):\$?(\d+)")
_re_col_range = re.compile(r"\$?([A-I]?[A-Z]):\$?([A-I]?[A-Z])", re.IGNORECASE)
_re_cell_range = re.compile(r"\$?([A-I]?[A-Z]\$?\d+):\$?([A-I]?[A-Z]\$?\d+)", re.IGNORECASE)
_re_cell_ref = re.compile(r"\$?([A-I]?[A-Z]\$?\d+)", re.IGNORECASE)


def col_by_name(colname):
    """'A' -> 0, 'Z' -> 25, 'AA' -> 26, etc
    """
    col = 0
    power = 1
    for i in xrange(len(colname)-1, -1, -1):
        ch = colname[i]
        col += (ord(ch) - ord('A') + 1) * power
        power *= 26
    return col - 1


def cell_to_rowcol(cell):
    """Convert an Excel cell reference string in A1 notation
    to numeric row/col notation.

    Returns: row, col, row_abs, col_abs

    """
    m = _re_cell_ex.match(cell)
    if not m:
        raise Exception("Ill-formed single_cell reference: %s" % cell)
    col_abs, col, row_abs, row = m.groups()
    row_abs = bool(row_abs)
    col_abs = bool(col_abs)
    row = int(row) - 1
    col = col_by_name(col.upper())
    return row, col, row_abs, col_abs


def cell_to_rowcol2(cell):
    """Convert an Excel cell reference string in A1 notation
    to numeric row/col notation.

    Returns: row, col

    """
    m = _re_cell_ex.match(cell)
    if not m:
        raise Exception("Error in cell format")
    col_abs, col, row_abs, row = m.groups()
    # Convert base26 column string to number
    # All your Base are belong to us.
    row = int(row) - 1
    col = col_by_name(col.upper())
    return row, col


def rowcol_to_cell(row, col, row_abs=False, col_abs=False):
    """Convert numeric row/col notation to an Excel cell reference string in
    A1 notation.

    """
    assert 0 <= row < MAX_ROW # MAX_ROW counts from 1
    assert 0 <= col < MAX_COL # MAX_COL counts from 1
    d = col // 26
    m = col % 26
    chr1 = ""    # Most significant character in AA1
    if row_abs:
        row_abs = '$'
    else:
        row_abs = ''
    if col_abs:
        col_abs = '$'
    else:
        col_abs = ''
    if d > 0:
        chr1 = chr(ord('A') + d  - 1)
    chr2 = chr(ord('A') + m)
    # Zero index to 1-index
    return col_abs + chr1 + chr2 + row_abs + str(row + 1)

def rowcol_pair_to_cellrange(row1, col1, row2, col2,
    row1_abs=False, col1_abs=False, row2_abs=False, col2_abs=False):
    """Convert two (row,column) pairs
    into a cell range string in A1:B2 notation.

    Returns: cell range string
    """
    assert row1 <= row2
    assert col1 <= col2
    return (
        rowcol_to_cell(row1, col1, row1_abs, col1_abs)
        + ":"
        + rowcol_to_cell(row2, col2, row2_abs, col2_abs)
        )

def cellrange_to_rowcol_pair(cellrange):
    """Convert cell range string in A1 notation to numeric row/col
    pair.

    Returns: row1, col1, row2, col2

    """
    cellrange = cellrange.upper()
    # Convert a row range: '1:3'
    res = _re_row_range.match(cellrange)
    if res:
        row1 = int(res.group(1)) - 1
        col1 = 0
        row2 = int(res.group(2)) - 1
        col2 = -1
        return row1, col1, row2, col2
    # Convert a column range: 'A:A' or 'B:G'.
    # A range such as A:A is equivalent to A1:A16384, so add rows as required
    res = _re_col_range.match(cellrange)
    if res:
        col1 = col_by_name(res.group(1).upper())
        row1 = 0
        col2 = col_by_name(res.group(2).upper())
        row2 = -1
        return row1, col1, row2, col2
    # Convert a cell range: 'A1:B7'
    res = _re_cell_range.match(cellrange)
    if res:
        row1, col1 = cell_to_rowcol2(res.group(1))
        row2, col2 = cell_to_rowcol2(res.group(2))
        return row1, col1, row2, col2
    # Convert a cell reference: 'A1' or 'AD2000'
    res = _re_cell_ref.match(cellrange)
    if res:
        row1, col1 = cell_to_rowcol2(res.group(1))
        return row1, col1, row1, col1
    raise Exception("Unknown cell reference %s" % (cellrange))


def cell_to_packed_rowcol(cell):
    """ pack row and column into the required 4 byte format """
    row, col, row_abs, col_abs = cell_to_rowcol(cell)
    if col >= MAX_COL:
        raise Exception("Column %s greater than IV in formula" % cell)
    if row >= MAX_ROW: # this for BIFF8. for BIFF7 available 2^14
        raise Exception("Row %s greater than %d in formula" % (cell, MAX_ROW))
    col |= int(not row_abs) << 15
    col |= int(not col_abs) << 14
    return row, col

# === sheetname functions ===

def valid_sheet_name(sheet_name):
    if sheet_name == u"" or sheet_name[0] == u"'" or len(sheet_name) > 31:
        return False
    for c in sheet_name:
        if c in u"[]:\\?/*\x00":
            return False
    return True

def quote_sheet_name(unquoted_sheet_name):
    if not valid_sheet_name(unquoted_sheet_name):
        raise Exception(
            'attempt to quote an invalid worksheet name %r' % unquoted_sheet_name)
    return u"'" + unquoted_sheet_name.replace(u"'", u"''") + u"'"
