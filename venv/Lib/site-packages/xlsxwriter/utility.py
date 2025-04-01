###############################################################################
#
# Worksheet - A class for writing Excel Worksheets.
#
# Copyright 2013-2018, John McNamara, jmcnamara@cpan.org
#
import re
import datetime
from warnings import warn

COL_NAMES = {}
range_parts = re.compile(r'(\$?)([A-Z]{1,3})(\$?)(\d+)')


def xl_rowcol_to_cell(row, col, row_abs=False, col_abs=False):
    """
    Convert a zero indexed row and column cell reference to a A1 style string.

    Args:
       row:     The cell row.    Int.
       col:     The cell column. Int.
       row_abs: Optional flag to make the row absolute.    Bool.
       col_abs: Optional flag to make the column absolute. Bool.

    Returns:
        A1 style string.

    """
    if row < 0:
        warn("Row number %d must be >= 0" % row)
        return None

    if col < 0:
        warn("Col number %d must be >= 0" % col)
        return None

    row += 1  # Change to 1-index.
    row_abs = '$' if row_abs else ''

    col_str = xl_col_to_name(col, col_abs)

    return col_str + row_abs + str(row)


def xl_rowcol_to_cell_fast(row, col):
    """
    Optimized version of the xl_rowcol_to_cell function. Only used internally.

    Args:
       row: The cell row.    Int.
       col: The cell column. Int.

    Returns:
        A1 style string.

    """
    if col in COL_NAMES:
        col_str = COL_NAMES[col]
    else:
        col_str = xl_col_to_name(col)
        COL_NAMES[col] = col_str

    return col_str + str(row + 1)


def xl_col_to_name(col, col_abs=False):
    """
    Convert a zero indexed column cell reference to a string.

    Args:
       col:     The cell column. Int.
       col_abs: Optional flag to make the column absolute. Bool.

    Returns:
        Column style string.

    """
    col_num = col
    if col_num < 0:
        warn("Col number %d must be >= 0" % col_num)
        return None

    col_num += 1  # Change to 1-index.
    col_str = ''
    col_abs = '$' if col_abs else ''

    while col_num:
        # Set remainder from 1 .. 26
        remainder = col_num % 26

        if remainder == 0:
            remainder = 26

        # Convert the remainder to a character.
        col_letter = chr(ord('A') + remainder - 1)

        # Accumulate the column letters, right to left.
        col_str = col_letter + col_str

        # Get the next order of magnitude.
        col_num = int((col_num - 1) / 26)

    return col_abs + col_str


def xl_cell_to_rowcol(cell_str):
    """
    Convert a cell reference in A1 notation to a zero indexed row and column.

    Args:
       cell_str:  A1 style string.

    Returns:
        row, col: Zero indexed cell row and column indices.

    """
    if not cell_str:
        return 0, 0

    match = range_parts.match(cell_str)
    col_str = match.group(2)
    row_str = match.group(4)

    # Convert base26 column string to number.
    expn = 0
    col = 0
    for char in reversed(col_str):
        col += (ord(char) - ord('A') + 1) * (26 ** expn)
        expn += 1

    # Convert 1-index to zero-index
    row = int(row_str) - 1
    col -= 1

    return row, col


def xl_cell_to_rowcol_abs(cell_str):
    """
    Convert an absolute cell reference in A1 notation to a zero indexed
    row and column, with True/False values for absolute rows or columns.

    Args:
       cell_str: A1 style string.

    Returns:
        row, col, row_abs, col_abs:  Zero indexed cell row and column indices.

    """
    if not cell_str:
        return 0, 0, False, False

    match = range_parts.match(cell_str)

    col_abs = match.group(1)
    col_str = match.group(2)
    row_abs = match.group(3)
    row_str = match.group(4)

    if col_abs:
        col_abs = True
    else:
        col_abs = False

    if row_abs:
        row_abs = True
    else:
        row_abs = False

    # Convert base26 column string to number.
    expn = 0
    col = 0
    for char in reversed(col_str):
        col += (ord(char) - ord('A') + 1) * (26 ** expn)
        expn += 1

    # Convert 1-index to zero-index
    row = int(row_str) - 1
    col -= 1

    return row, col, row_abs, col_abs


def xl_range(first_row, first_col, last_row, last_col):
    """
    Convert zero indexed row and col cell references to a A1:B1 range string.

    Args:
       first_row: The first cell row.    Int.
       first_col: The first cell column. Int.
       last_row:  The last cell row.     Int.
       last_col:  The last cell column.  Int.

    Returns:
        A1:B1 style range string.

    """
    range1 = xl_rowcol_to_cell(first_row, first_col)
    range2 = xl_rowcol_to_cell(last_row, last_col)

    if range1 is None or range2 is None:
        warn("Row and column numbers must be >= 0")
        return None

    return range1 + ':' + range2


def xl_range_abs(first_row, first_col, last_row, last_col):
    """
    Convert zero indexed row and col cell references to a $A$1:$B$1 absolute
    range string.

    Args:
       first_row: The first cell row.    Int.
       first_col: The first cell column. Int.
       last_row:  The last cell row.     Int.
       last_col:  The last cell column.  Int.

    Returns:
        $A$1:$B$1 style range string.

    """
    range1 = xl_rowcol_to_cell(first_row, first_col, True, True)
    range2 = xl_rowcol_to_cell(last_row, last_col, True, True)

    if range1 is None or range2 is None:
        warn("Row and column numbers must be >= 0")
        return None

    return range1 + ':' + range2


def xl_range_formula(sheetname, first_row, first_col, last_row, last_col):
    """
    Convert worksheet name and zero indexed row and col cell references to
    a Sheet1!A1:B1 range formula string.

    Args:
       sheetname: The worksheet name.    String.
       first_row: The first cell row.    Int.
       first_col: The first cell column. Int.
       last_row:  The last cell row.     Int.
       last_col:  The last cell column.  Int.

    Returns:
        A1:B1 style range string.

    """
    cell_range = xl_range_abs(first_row, first_col, last_row, last_col)
    sheetname = quote_sheetname(sheetname)

    return sheetname + '!' + cell_range


def quote_sheetname(sheetname):
    """
    Convert a worksheet name to a quoted  name if it contains spaces or
    special characters.

    Args:
       sheetname: The worksheet name. String.

    Returns:
        A quoted worksheet string.

    """

    # TODO. Possibly extend this to quote sheetnames that look like ranges.
    if not sheetname.isalnum() and not sheetname.startswith("'"):
        # Double quote any single quotes.
        sheetname = sheetname.replace("'", "''")

        # Singe quote the sheet name.
        sheetname = "'%s'" % sheetname

    return sheetname


def xl_color(color):
    # Used in conjunction with the XlsxWriter *color() methods to convert
    # a color name into an RGB formatted string. These colors are for
    # backward compatibility with older versions of Excel.
    named_colors = {
        'black': '#000000',
        'blue': '#0000FF',
        'brown': '#800000',
        'cyan': '#00FFFF',
        'gray': '#808080',
        'green': '#008000',
        'lime': '#00FF00',
        'magenta': '#FF00FF',
        'navy': '#000080',
        'orange': '#FF6600',
        'pink': '#FF00FF',
        'purple': '#800080',
        'red': '#FF0000',
        'silver': '#C0C0C0',
        'white': '#FFFFFF',
        'yellow': '#FFFF00',
    }

    if color in named_colors:
        color = named_colors[color]

    if not re.match('#[0-9a-fA-F]{6}', color):
        warn("Color '%s' isn't a valid Excel color" % color)

    # Convert the RGB color to the Excel ARGB format.
    return "FF" + color.lstrip('#').upper()


def get_rgb_color(color):
    # Convert the user specified color to an RGB color.
    rgb_color = xl_color(color)

    # Remove leading FF from RGB color for charts.
    rgb_color = re.sub(r'^FF', '', rgb_color)

    return rgb_color


def get_sparkline_style(style_id):
    styles = [
        {'series':   {'theme': "4", 'tint': "-0.499984740745262"},
         'negative': {'theme': "5"},
         'markers':  {'theme': "4", 'tint': "-0.499984740745262"},
         'first':    {'theme': "4", 'tint': "0.39997558519241921"},
         'last':     {'theme': "4", 'tint': "0.39997558519241921"},
         'high':     {'theme': "4"},
         'low':      {'theme': "4"},
         },  # 0
        {'series':   {'theme': "4", 'tint': "-0.499984740745262"},
         'negative': {'theme': "5"},
         'markers':  {'theme': "4", 'tint': "-0.499984740745262"},
         'first':    {'theme': "4", 'tint': "0.39997558519241921"},
         'last':     {'theme': "4", 'tint': "0.39997558519241921"},
         'high':     {'theme': "4"},
         'low':      {'theme': "4"},
         },  # 1
        {'series':   {'theme': "5", 'tint': "-0.499984740745262"},
         'negative': {'theme': "6"},
         'markers':  {'theme': "5", 'tint': "-0.499984740745262"},
         'first':    {'theme': "5", 'tint': "0.39997558519241921"},
         'last':     {'theme': "5", 'tint': "0.39997558519241921"},
         'high':     {'theme': "5"},
         'low':      {'theme': "5"},
         },  # 2
        {'series':   {'theme': "6", 'tint': "-0.499984740745262"},
         'negative': {'theme': "7"},
         'markers':  {'theme': "6", 'tint': "-0.499984740745262"},
         'first':    {'theme': "6", 'tint': "0.39997558519241921"},
         'last':     {'theme': "6", 'tint': "0.39997558519241921"},
         'high':     {'theme': "6"},
         'low':      {'theme': "6"},
         },  # 3
        {'series':   {'theme': "7", 'tint': "-0.499984740745262"},
         'negative': {'theme': "8"},
         'markers':  {'theme': "7", 'tint': "-0.499984740745262"},
         'first':    {'theme': "7", 'tint': "0.39997558519241921"},
         'last':     {'theme': "7", 'tint': "0.39997558519241921"},
         'high':     {'theme': "7"},
         'low':      {'theme': "7"},
         },  # 4
        {'series':   {'theme': "8", 'tint': "-0.499984740745262"},
         'negative': {'theme': "9"},
         'markers':  {'theme': "8", 'tint': "-0.499984740745262"},
         'first':    {'theme': "8", 'tint': "0.39997558519241921"},
         'last':     {'theme': "8", 'tint': "0.39997558519241921"},
         'high':     {'theme': "8"},
         'low':      {'theme': "8"},
         },  # 5
        {'series':   {'theme': "9", 'tint': "-0.499984740745262"},
         'negative': {'theme': "4"},
         'markers':  {'theme': "9", 'tint': "-0.499984740745262"},
         'first':    {'theme': "9", 'tint': "0.39997558519241921"},
         'last':     {'theme': "9", 'tint': "0.39997558519241921"},
         'high':     {'theme': "9"},
         'low':      {'theme': "9"},
         },  # 6
        {'series':   {'theme': "4", 'tint': "-0.249977111117893"},
         'negative': {'theme': "5"},
         'markers':  {'theme': "5", 'tint': "-0.249977111117893"},
         'first':    {'theme': "5", 'tint': "-0.249977111117893"},
         'last':     {'theme': "5", 'tint': "-0.249977111117893"},
         'high':     {'theme': "5", 'tint': "-0.249977111117893"},
         'low':      {'theme': "5", 'tint': "-0.249977111117893"},
         },  # 7
        {'series':   {'theme': "5", 'tint': "-0.249977111117893"},
         'negative': {'theme': "6"},
         'markers':  {'theme': "6", 'tint': "-0.249977111117893"},
         'first':    {'theme': "6", 'tint': "-0.249977111117893"},
         'last':     {'theme': "6", 'tint': "-0.249977111117893"},
         'high':     {'theme': "6", 'tint': "-0.249977111117893"},
         'low':      {'theme': "6", 'tint': "-0.249977111117893"},
         },  # 8
        {'series':   {'theme': "6", 'tint': "-0.249977111117893"},
         'negative': {'theme': "7"},
         'markers':  {'theme': "7", 'tint': "-0.249977111117893"},
         'first':    {'theme': "7", 'tint': "-0.249977111117893"},
         'last':     {'theme': "7", 'tint': "-0.249977111117893"},
         'high':     {'theme': "7", 'tint': "-0.249977111117893"},
         'low':      {'theme': "7", 'tint': "-0.249977111117893"},
         },  # 9
        {'series':   {'theme': "7", 'tint': "-0.249977111117893"},
         'negative': {'theme': "8"},
         'markers':  {'theme': "8", 'tint': "-0.249977111117893"},
         'first':    {'theme': "8", 'tint': "-0.249977111117893"},
         'last':     {'theme': "8", 'tint': "-0.249977111117893"},
         'high':     {'theme': "8", 'tint': "-0.249977111117893"},
         'low':      {'theme': "8", 'tint': "-0.249977111117893"},
         },  # 10
        {'series':   {'theme': "8", 'tint': "-0.249977111117893"},
         'negative': {'theme': "9"},
         'markers':  {'theme': "9", 'tint': "-0.249977111117893"},
         'first':    {'theme': "9", 'tint': "-0.249977111117893"},
         'last':     {'theme': "9", 'tint': "-0.249977111117893"},
         'high':     {'theme': "9", 'tint': "-0.249977111117893"},
         'low':      {'theme': "9", 'tint': "-0.249977111117893"},
         },  # 11
        {'series':   {'theme': "9", 'tint': "-0.249977111117893"},
         'negative': {'theme': "4"},
         'markers':  {'theme': "4", 'tint': "-0.249977111117893"},
         'first':    {'theme': "4", 'tint': "-0.249977111117893"},
         'last':     {'theme': "4", 'tint': "-0.249977111117893"},
         'high':     {'theme': "4", 'tint': "-0.249977111117893"},
         'low':      {'theme': "4", 'tint': "-0.249977111117893"},
         },  # 12
        {'series':   {'theme': "4"},
         'negative': {'theme': "5"},
         'markers':  {'theme': "4", 'tint': "-0.249977111117893"},
         'first':    {'theme': "4", 'tint': "-0.249977111117893"},
         'last':     {'theme': "4", 'tint': "-0.249977111117893"},
         'high':     {'theme': "4", 'tint': "-0.249977111117893"},
         'low':      {'theme': "4", 'tint': "-0.249977111117893"},
         },  # 13
        {'series':   {'theme': "5"},
         'negative': {'theme': "6"},
         'markers':  {'theme': "5", 'tint': "-0.249977111117893"},
         'first':    {'theme': "5", 'tint': "-0.249977111117893"},
         'last':     {'theme': "5", 'tint': "-0.249977111117893"},
         'high':     {'theme': "5", 'tint': "-0.249977111117893"},
         'low':      {'theme': "5", 'tint': "-0.249977111117893"},
         },  # 14
        {'series':   {'theme': "6"},
         'negative': {'theme': "7"},
         'markers':  {'theme': "6", 'tint': "-0.249977111117893"},
         'first':    {'theme': "6", 'tint': "-0.249977111117893"},
         'last':     {'theme': "6", 'tint': "-0.249977111117893"},
         'high':     {'theme': "6", 'tint': "-0.249977111117893"},
         'low':      {'theme': "6", 'tint': "-0.249977111117893"},
         },  # 15
        {'series':   {'theme': "7"},
         'negative': {'theme': "8"},
         'markers':  {'theme': "7", 'tint': "-0.249977111117893"},
         'first':    {'theme': "7", 'tint': "-0.249977111117893"},
         'last':     {'theme': "7", 'tint': "-0.249977111117893"},
         'high':     {'theme': "7", 'tint': "-0.249977111117893"},
         'low':      {'theme': "7", 'tint': "-0.249977111117893"},
         },  # 16
        {'series':   {'theme': "8"},
         'negative': {'theme': "9"},
         'markers':  {'theme': "8", 'tint': "-0.249977111117893"},
         'first':    {'theme': "8", 'tint': "-0.249977111117893"},
         'last':     {'theme': "8", 'tint': "-0.249977111117893"},
         'high':     {'theme': "8", 'tint': "-0.249977111117893"},
         'low':      {'theme': "8", 'tint': "-0.249977111117893"},
         },  # 17
        {'series':   {'theme': "9"},
         'negative': {'theme': "4"},
         'markers':  {'theme': "9", 'tint': "-0.249977111117893"},
         'first':    {'theme': "9", 'tint': "-0.249977111117893"},
         'last':     {'theme': "9", 'tint': "-0.249977111117893"},
         'high':     {'theme': "9", 'tint': "-0.249977111117893"},
         'low':      {'theme': "9", 'tint': "-0.249977111117893"},
         },  # 18
        {'series':   {'theme': "4", 'tint': "0.39997558519241921"},
         'negative': {'theme': "0", 'tint': "-0.499984740745262"},
         'markers':  {'theme': "4", 'tint': "0.79998168889431442"},
         'first':    {'theme': "4", 'tint': "-0.249977111117893"},
         'last':     {'theme': "4", 'tint': "-0.249977111117893"},
         'high':     {'theme': "4", 'tint': "-0.499984740745262"},
         'low':      {'theme': "4", 'tint': "-0.499984740745262"},
         },  # 19
        {'series':   {'theme': "5", 'tint': "0.39997558519241921"},
         'negative': {'theme': "0", 'tint': "-0.499984740745262"},
         'markers':  {'theme': "5", 'tint': "0.79998168889431442"},
         'first':    {'theme': "5", 'tint': "-0.249977111117893"},
         'last':     {'theme': "5", 'tint': "-0.249977111117893"},
         'high':     {'theme': "5", 'tint': "-0.499984740745262"},
         'low':      {'theme': "5", 'tint': "-0.499984740745262"},
         },  # 20
        {'series':   {'theme': "6", 'tint': "0.39997558519241921"},
         'negative': {'theme': "0", 'tint': "-0.499984740745262"},
         'markers':  {'theme': "6", 'tint': "0.79998168889431442"},
         'first':    {'theme': "6", 'tint': "-0.249977111117893"},
         'last':     {'theme': "6", 'tint': "-0.249977111117893"},
         'high':     {'theme': "6", 'tint': "-0.499984740745262"},
         'low':      {'theme': "6", 'tint': "-0.499984740745262"},
         },  # 21
        {'series':   {'theme': "7", 'tint': "0.39997558519241921"},
         'negative': {'theme': "0", 'tint': "-0.499984740745262"},
         'markers':  {'theme': "7", 'tint': "0.79998168889431442"},
         'first':    {'theme': "7", 'tint': "-0.249977111117893"},
         'last':     {'theme': "7", 'tint': "-0.249977111117893"},
         'high':     {'theme': "7", 'tint': "-0.499984740745262"},
         'low':      {'theme': "7", 'tint': "-0.499984740745262"},
         },  # 22
        {'series':   {'theme': "8", 'tint': "0.39997558519241921"},
         'negative': {'theme': "0", 'tint': "-0.499984740745262"},
         'markers':  {'theme': "8", 'tint': "0.79998168889431442"},
         'first':    {'theme': "8", 'tint': "-0.249977111117893"},
         'last':     {'theme': "8", 'tint': "-0.249977111117893"},
         'high':     {'theme': "8", 'tint': "-0.499984740745262"},
         'low':      {'theme': "8", 'tint': "-0.499984740745262"},
         },  # 23
        {'series':   {'theme': "9", 'tint': "0.39997558519241921"},
         'negative': {'theme': "0", 'tint': "-0.499984740745262"},
         'markers':  {'theme': "9", 'tint': "0.79998168889431442"},
         'first':    {'theme': "9", 'tint': "-0.249977111117893"},
         'last':     {'theme': "9", 'tint': "-0.249977111117893"},
         'high':     {'theme': "9", 'tint': "-0.499984740745262"},
         'low':      {'theme': "9", 'tint': "-0.499984740745262"},
         },  # 24
        {'series':   {'theme': "1", 'tint': "0.499984740745262"},
         'negative': {'theme': "1", 'tint': "0.249977111117893"},
         'markers':  {'theme': "1", 'tint': "0.249977111117893"},
         'first':    {'theme': "1", 'tint': "0.249977111117893"},
         'last':     {'theme': "1", 'tint': "0.249977111117893"},
         'high':     {'theme': "1", 'tint': "0.249977111117893"},
         'low':      {'theme': "1", 'tint': "0.249977111117893"},
         },  # 25
        {'series':   {'theme': "1", 'tint': "0.34998626667073579"},
         'negative': {'theme': "0", 'tint': "-0.249977111117893"},
         'markers':  {'theme': "0", 'tint': "-0.249977111117893"},
         'first':    {'theme': "0", 'tint': "-0.249977111117893"},
         'last':     {'theme': "0", 'tint': "-0.249977111117893"},
         'high':     {'theme': "0", 'tint': "-0.249977111117893"},
         'low':      {'theme': "0", 'tint': "-0.249977111117893"},
         },  # 26
        {'series':   {'rgb': "FF323232"},
         'negative': {'rgb': "FFD00000"},
         'markers':  {'rgb': "FFD00000"},
         'first':    {'rgb': "FFD00000"},
         'last':     {'rgb': "FFD00000"},
         'high':     {'rgb': "FFD00000"},
         'low':      {'rgb': "FFD00000"},
         },  # 27
        {'series':   {'rgb': "FF000000"},
         'negative': {'rgb': "FF0070C0"},
         'markers':  {'rgb': "FF0070C0"},
         'first':    {'rgb': "FF0070C0"},
         'last':     {'rgb': "FF0070C0"},
         'high':     {'rgb': "FF0070C0"},
         'low':      {'rgb': "FF0070C0"},
         },  # 28
        {'series':   {'rgb': "FF376092"},
         'negative': {'rgb': "FFD00000"},
         'markers':  {'rgb': "FFD00000"},
         'first':    {'rgb': "FFD00000"},
         'last':     {'rgb': "FFD00000"},
         'high':     {'rgb': "FFD00000"},
         'low':      {'rgb': "FFD00000"},
         },  # 29
        {'series':   {'rgb': "FF0070C0"},
         'negative': {'rgb': "FF000000"},
         'markers':  {'rgb': "FF000000"},
         'first':    {'rgb': "FF000000"},
         'last':     {'rgb': "FF000000"},
         'high':     {'rgb': "FF000000"},
         'low':      {'rgb': "FF000000"},
         },  # 30
        {'series':   {'rgb': "FF5F5F5F"},
         'negative': {'rgb': "FFFFB620"},
         'markers':  {'rgb': "FFD70077"},
         'first':    {'rgb': "FF5687C2"},
         'last':     {'rgb': "FF359CEB"},
         'high':     {'rgb': "FF56BE79"},
         'low':      {'rgb': "FFFF5055"},
         },  # 31
        {'series':   {'rgb': "FF5687C2"},
         'negative': {'rgb': "FFFFB620"},
         'markers':  {'rgb': "FFD70077"},
         'first':    {'rgb': "FF777777"},
         'last':     {'rgb': "FF359CEB"},
         'high':     {'rgb': "FF56BE79"},
         'low':      {'rgb': "FFFF5055"},
         },  # 32
        {'series':   {'rgb': "FFC6EFCE"},
         'negative': {'rgb': "FFFFC7CE"},
         'markers':  {'rgb': "FF8CADD6"},
         'first':    {'rgb': "FFFFDC47"},
         'last':     {'rgb': "FFFFEB9C"},
         'high':     {'rgb': "FF60D276"},
         'low':      {'rgb': "FFFF5367"},
         },  # 33
        {'series':   {'rgb': "FF00B050"},
         'negative': {'rgb': "FFFF0000"},
         'markers':  {'rgb': "FF0070C0"},
         'first':    {'rgb': "FFFFC000"},
         'last':     {'rgb': "FFFFC000"},
         'high':     {'rgb': "FF00B050"},
         'low':      {'rgb': "FFFF0000"},
         },  # 34
        {'series':   {'theme': "3"},
         'negative': {'theme': "9"},
         'markers':  {'theme': "8"},
         'first':    {'theme': "4"},
         'last':     {'theme': "5"},
         'high':     {'theme': "6"},
         'low':      {'theme': "7"},
         },  # 35
        {'series':   {'theme': "1"},
         'negative': {'theme': "9"},
         'markers':  {'theme': "8"},
         'first':    {'theme': "4"},
         'last':     {'theme': "5"},
         'high':     {'theme': "6"},
         'low':      {'theme': "7"},
         },  # 36
    ]

    return styles[style_id]


def supported_datetime(dt):
    # Determine is an argument is a supported datetime object.
    return(isinstance(dt, (datetime.datetime,
                           datetime.date,
                           datetime.time,
                           datetime.timedelta)))


def remove_datetime_timezone(dt_obj, remove_timezone):
    # Excel doesn't support timezones in datetimes/times so we remove the
    # tzinfo from the object if the user has specified that option in the
    # constructor.
    if remove_timezone:
        dt_obj = dt_obj.replace(tzinfo=None)
    else:
        if dt_obj.tzinfo:
            raise TypeError(
                "Excel doesn't support timezones in datetimes. "
                "Set the tzinfo in the datetime/time object to None or "
                "use the 'remove_timezone' Workbook() option")

    return dt_obj


def datetime_to_excel_datetime(dt_obj, date_1904, remove_timezone):
    # Convert a datetime object to an Excel serial date and time. The integer
    # part of the number stores the number of days since the epoch and the
    # fractional part stores the percentage of the day.
    date_type = dt_obj

    if date_1904:
        # Excel for Mac date epoch.
        epoch = datetime.datetime(1904, 1, 1)
    else:
        # Default Excel epoch.
        epoch = datetime.datetime(1899, 12, 31)

    # We handle datetime .datetime, .date and .time objects but convert
    # them to datetime.datetime objects and process them in the same way.
    if isinstance(dt_obj, datetime.datetime):
        dt_obj = remove_datetime_timezone(dt_obj, remove_timezone)
        delta = dt_obj - epoch
    elif isinstance(dt_obj, datetime.date):
        dt_obj = datetime.datetime.fromordinal(dt_obj.toordinal())
        delta = dt_obj - epoch
    elif isinstance(dt_obj, datetime.time):
        dt_obj = datetime.datetime.combine(epoch, dt_obj)
        dt_obj = remove_datetime_timezone(dt_obj, remove_timezone)
        delta = dt_obj - epoch
    elif isinstance(dt_obj, datetime.timedelta):
        delta = dt_obj
    else:
        raise TypeError("Unknown or unsupported datetime type")

    # Convert a Python datetime.datetime value to an Excel date number.
    excel_time = (delta.days
                  + (float(delta.seconds)
                     + float(delta.microseconds) / 1E6)
                  / (60 * 60 * 24))

    # The following is a workaround for the fact that in Excel a time only
    # value is represented as 1899-12-31+time whereas in datetime.datetime()
    # it is 1900-1-1+time so we need to subtract the 1 day difference.
    if (isinstance(date_type, datetime.datetime)
            and dt_obj.isocalendar() == (1900, 1, 1)):
        excel_time -= 1

    # Account for Excel erroneously treating 1900 as a leap year.
    if not date_1904 and excel_time > 59:
        excel_time += 1

    return excel_time
