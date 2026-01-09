###############################################################################
#
# Worksheet - A class for writing the Excel XLSX Worksheet file.
#
# SPDX-License-Identifier: BSD-2-Clause
# Copyright 2013-2023, John McNamara, jmcnamara@cpan.org
#

# Standard packages.
import datetime
import math
import os
import re
import tempfile

from collections import defaultdict
from collections import namedtuple
from decimal import Decimal
from fractions import Fraction
from functools import wraps
from io import StringIO
from math import isinf
from math import isnan
from warnings import warn

# Package imports.
from . import xmlwriter
from .format import Format
from .drawing import Drawing
from .shape import Shape
from .xmlwriter import XMLwriter
from .utility import xl_rowcol_to_cell
from .utility import xl_rowcol_to_cell_fast
from .utility import xl_cell_to_rowcol
from .utility import xl_col_to_name
from .utility import xl_range
from .utility import xl_color
from .utility import xl_pixel_width
from .utility import get_sparkline_style
from .utility import supported_datetime
from .utility import datetime_to_excel_datetime
from .utility import preserve_whitespace
from .utility import quote_sheetname
from .exceptions import DuplicateTableName
from .exceptions import OverlappingRange

# Compile performance critical regular expressions.
re_control_chars_1 = re.compile("(_x[0-9a-fA-F]{4}_)")
re_control_chars_2 = re.compile(r"([\x00-\x08\x0b-\x1f])")

re_dynamic_function = re.compile(
    r"""
    \bANCHORARRAY\(    |
    \bBYCOL\(          |
    \bBYROW\(          |
    \bCHOOSECOLS\(     |
    \bCHOOSEROWS\(     |
    \bDROP\(           |
    \bEXPAND\(         |
    \bFILTER\(         |
    \bHSTACK\(         |
    \bLAMBDA\(         |
    \bMAKEARRAY\(      |
    \bMAP\(            |
    \bRANDARRAY\(      |
    \bREDUCE\(         |
    \bSCAN\(           |
    \bSEQUENCE\(       |
    \bSINGLE\(         |
    \bSORT\(           |
    \bSORTBY\(         |
    \bSWITCH\(         |
    \bTAKE\(           |
    \bTEXTSPLIT\(      |
    \bTOCOL\(          |
    \bTOROW\(          |
    \bUNIQUE\(         |
    \bVSTACK\(         |
    \bWRAPCOLS\(       |
    \bWRAPROWS\(       |
    \bXLOOKUP\(""",
    re.VERBOSE,
)


###############################################################################
#
# Decorator functions.
#
###############################################################################
def convert_cell_args(method):
    """
    Decorator function to convert A1 notation in cell method calls
    to the default row/col notation.

    """

    @wraps(method)
    def cell_wrapper(self, *args, **kwargs):
        try:
            # First arg is an int, default to row/col notation.
            if args:
                first_arg = args[0]
                int(first_arg)
        except ValueError:
            # First arg isn't an int, convert to A1 notation.
            new_args = xl_cell_to_rowcol(first_arg)
            args = new_args + args[1:]

        return method(self, *args, **kwargs)

    return cell_wrapper


def convert_range_args(method):
    """
    Decorator function to convert A1 notation in range method calls
    to the default row/col notation.

    """

    @wraps(method)
    def cell_wrapper(self, *args, **kwargs):
        try:
            # First arg is an int, default to row/col notation.
            if args:
                int(args[0])
        except ValueError:
            # First arg isn't an int, convert to A1 notation.
            if ":" in args[0]:
                cell_1, cell_2 = args[0].split(":")
                row_1, col_1 = xl_cell_to_rowcol(cell_1)
                row_2, col_2 = xl_cell_to_rowcol(cell_2)
            else:
                row_1, col_1 = xl_cell_to_rowcol(args[0])
                row_2, col_2 = row_1, col_1

            new_args = [row_1, col_1, row_2, col_2]
            new_args.extend(args[1:])
            args = new_args

        return method(self, *args, **kwargs)

    return cell_wrapper


def convert_column_args(method):
    """
    Decorator function to convert A1 notation in columns method calls
    to the default row/col notation.

    """

    @wraps(method)
    def column_wrapper(self, *args, **kwargs):
        try:
            # First arg is an int, default to row/col notation.
            if args:
                int(args[0])
        except ValueError:
            # First arg isn't an int, convert to A1 notation.
            cell_1, cell_2 = [col + "1" for col in args[0].split(":")]
            _, col_1 = xl_cell_to_rowcol(cell_1)
            _, col_2 = xl_cell_to_rowcol(cell_2)
            new_args = [col_1, col_2]
            new_args.extend(args[1:])
            args = new_args

        return method(self, *args, **kwargs)

    return column_wrapper


###############################################################################
#
# Named tuples used for cell types.
#
###############################################################################
cell_string_tuple = namedtuple("String", "string, format")
cell_number_tuple = namedtuple("Number", "number, format")
cell_blank_tuple = namedtuple("Blank", "format")
cell_boolean_tuple = namedtuple("Boolean", "boolean, format")
cell_formula_tuple = namedtuple("Formula", "formula, format, value")
cell_datetime_tuple = namedtuple("Datetime", "number, format")
cell_arformula_tuple = namedtuple(
    "ArrayFormula", "formula, format, value, range, atype"
)
cell_rich_string_tuple = namedtuple("RichString", "string, format, raw_string")


###############################################################################
#
# Worksheet Class definition.
#
###############################################################################
class Worksheet(xmlwriter.XMLwriter):
    """
    A class for writing the Excel XLSX Worksheet file.

    """

    ###########################################################################
    #
    # Public API.
    #
    ###########################################################################

    def __init__(self):
        """
        Constructor.

        """

        super(Worksheet, self).__init__()

        self.name = None
        self.index = None
        self.str_table = None
        self.palette = None
        self.constant_memory = 0
        self.tmpdir = None
        self.is_chartsheet = False

        self.ext_sheets = []
        self.fileclosed = 0
        self.excel_version = 2007
        self.excel2003_style = False

        self.xls_rowmax = 1048576
        self.xls_colmax = 16384
        self.xls_strmax = 32767
        self.dim_rowmin = None
        self.dim_rowmax = None
        self.dim_colmin = None
        self.dim_colmax = None

        self.col_info = {}
        self.selections = []
        self.hidden = 0
        self.active = 0
        self.tab_color = 0
        self.top_left_cell = ""

        self.panes = []
        self.active_pane = 3
        self.selected = 0

        self.page_setup_changed = False
        self.paper_size = 0
        self.orientation = 1

        self.print_options_changed = False
        self.hcenter = False
        self.vcenter = False
        self.print_gridlines = False
        self.screen_gridlines = True
        self.print_headers = False
        self.row_col_headers = False

        self.header_footer_changed = False
        self.header = ""
        self.footer = ""
        self.header_footer_aligns = True
        self.header_footer_scales = True
        self.header_images = []
        self.footer_images = []
        self.header_images_list = []

        self.margin_left = 0.7
        self.margin_right = 0.7
        self.margin_top = 0.75
        self.margin_bottom = 0.75
        self.margin_header = 0.3
        self.margin_footer = 0.3

        self.repeat_row_range = ""
        self.repeat_col_range = ""
        self.print_area_range = ""

        self.page_order = 0
        self.black_white = 0
        self.draft_quality = 0
        self.print_comments = 0
        self.page_start = 0

        self.fit_page = 0
        self.fit_width = 0
        self.fit_height = 0

        self.hbreaks = []
        self.vbreaks = []

        self.protect_options = {}
        self.protected_ranges = []
        self.num_protected_ranges = 0
        self.set_cols = {}
        self.set_rows = defaultdict(dict)

        self.zoom = 100
        self.zoom_scale_normal = 1
        self.print_scale = 100
        self.is_right_to_left = 0
        self.show_zeros = 1
        self.leading_zeros = 0

        self.outline_row_level = 0
        self.outline_col_level = 0
        self.outline_style = 0
        self.outline_below = 1
        self.outline_right = 1
        self.outline_on = 1
        self.outline_changed = False

        self.original_row_height = 15
        self.default_row_height = 15
        self.default_row_pixels = 20
        self.default_col_width = 8.43
        self.default_col_pixels = 64
        self.default_date_pixels = 68
        self.default_row_zeroed = 0

        self.names = {}
        self.write_match = []
        self.table = defaultdict(dict)
        self.merge = []
        self.merged_cells = {}
        self.table_cells = {}
        self.row_spans = {}

        self.has_vml = False
        self.has_header_vml = False
        self.has_comments = False
        self.comments = defaultdict(dict)
        self.comments_list = []
        self.comments_author = ""
        self.comments_visible = 0
        self.vml_shape_id = 1024
        self.buttons_list = []
        self.vml_header_id = 0

        self.autofilter_area = ""
        self.autofilter_ref = None
        self.filter_range = []
        self.filter_on = 0
        self.filter_cols = {}
        self.filter_type = {}
        self.filter_cells = {}

        self.row_sizes = {}
        self.col_size_changed = False
        self.row_size_changed = False

        self.last_shape_id = 1
        self.rel_count = 0
        self.hlink_count = 0
        self.hlink_refs = []
        self.external_hyper_links = []
        self.external_drawing_links = []
        self.external_comment_links = []
        self.external_vml_links = []
        self.external_table_links = []
        self.external_background_links = []
        self.drawing_links = []
        self.vml_drawing_links = []
        self.charts = []
        self.images = []
        self.tables = []
        self.sparklines = []
        self.shapes = []
        self.shape_hash = {}
        self.drawing = 0
        self.drawing_rels = {}
        self.drawing_rels_id = 0
        self.vml_drawing_rels = {}
        self.vml_drawing_rels_id = 0
        self.background_image = None
        self.background_bytes = False

        self.rstring = ""
        self.previous_row = 0

        self.validations = []
        self.cond_formats = {}
        self.data_bars_2010 = []
        self.use_data_bars_2010 = False
        self.dxf_priority = 1
        self.page_view = 0

        self.vba_codename = None

        self.date_1904 = False
        self.hyperlinks = defaultdict(dict)

        self.strings_to_numbers = False
        self.strings_to_urls = True
        self.nan_inf_to_errors = False
        self.strings_to_formulas = True

        self.default_date_format = None
        self.default_url_format = None
        self.remove_timezone = False
        self.max_url_length = 2079

        self.row_data_filename = None
        self.row_data_fh = None
        self.worksheet_meta = None
        self.vml_data_id = None
        self.vml_shape_id = None

        self.row_data_filename = None
        self.row_data_fh = None
        self.row_data_fh_closed = False

        self.vertical_dpi = 0
        self.horizontal_dpi = 0

        self.write_handlers = {}

        self.ignored_errors = None

        self.has_dynamic_arrays = False
        self.use_future_functions = False

    # Utility function for writing different types of strings.
    def _write_token_as_string(self, token, row, col, *args):
        # Map the data to the appropriate write_*() method.
        if token == "":
            return self._write_blank(row, col, *args)

        if self.strings_to_formulas and token.startswith("="):
            return self._write_formula(row, col, *args)

        if token.startswith("{=") and token.endswith("}"):
            return self._write_formula(row, col, *args)

        if (
            ":" in token
            and self.strings_to_urls
            and (
                re.match("(ftp|http)s?://", token)
                or re.match("mailto:", token)
                or re.match("(in|ex)ternal:", token)
            )
        ):
            return self._write_url(row, col, *args)

        if self.strings_to_numbers:
            try:
                f = float(token)
                if self.nan_inf_to_errors or (not isnan(f) and not isinf(f)):
                    return self._write_number(row, col, f, *args[1:])
            except ValueError:
                # Not a number, write as a string.
                pass

            return self._write_string(row, col, *args)

        else:
            # We have a plain string.
            return self._write_string(row, col, *args)

    @convert_cell_args
    def write(self, row, col, *args):
        """
        Write data to a worksheet cell by calling the appropriate write_*()
        method based on the type of data being passed.

        Args:
            row:   The cell row (zero indexed).
            col:   The cell column (zero indexed).
            *args: Args to pass to sub functions.

        Returns:
             0:    Success.
            -1:    Row or column is out of worksheet bounds.
            other: Return value of called method.

        """
        return self._write(row, col, *args)

    # Undecorated version of write().
    def _write(self, row, col, *args):
        # Check the number of args passed.
        if not args:
            raise TypeError("write() takes at least 4 arguments (3 given)")

        # The first arg should be the token for all write calls.
        token = args[0]

        # Avoid isinstance() for better performance.
        token_type = token.__class__

        # Check for any user defined type handlers with callback functions.
        if token_type in self.write_handlers:
            write_handler = self.write_handlers[token_type]
            function_return = write_handler(self, row, col, *args)

            # If the return value is None then the callback has returned
            # control to this function and we should continue as
            # normal. Otherwise we return the value to the caller and exit.
            if function_return is None:
                pass
            else:
                return function_return

        # Write None as a blank cell.
        if token is None:
            return self._write_blank(row, col, *args)

        # Check for standard Python types.
        if token_type is bool:
            return self._write_boolean(row, col, *args)

        if token_type in (float, int, Decimal, Fraction):
            return self._write_number(row, col, *args)

        if token_type is str:
            return self._write_token_as_string(token, row, col, *args)

        if token_type in (
            datetime.datetime,
            datetime.date,
            datetime.time,
            datetime.timedelta,
        ):
            return self._write_datetime(row, col, *args)

        # Resort to isinstance() for subclassed primitives.

        # Write number types.
        if isinstance(token, (float, int, Decimal, Fraction)):
            return self._write_number(row, col, *args)

        # Write string types.
        if isinstance(token, str):
            return self._write_token_as_string(token, row, col, *args)

        # Write boolean types.
        if isinstance(token, bool):
            return self._write_boolean(row, col, *args)

        # Write datetime objects.
        if supported_datetime(token):
            return self._write_datetime(row, col, *args)

        # We haven't matched a supported type. Try float.
        try:
            f = float(token)
            return self._write_number(row, col, f, *args[1:])
        except ValueError:
            pass
        except TypeError:
            raise TypeError("Unsupported type %s in write()" % type(token))

        # Finally try string.
        try:
            str(token)
            return self._write_string(row, col, *args)
        except ValueError:
            raise TypeError("Unsupported type %s in write()" % type(token))

    @convert_cell_args
    def write_string(self, row, col, string, cell_format=None):
        """
        Write a string to a worksheet cell.

        Args:
            row:    The cell row (zero indexed).
            col:    The cell column (zero indexed).
            string: Cell data. Str.
            format: An optional cell Format object.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.
            -2: String truncated to 32k characters.

        """
        return self._write_string(row, col, string, cell_format)

    # Undecorated version of write_string().
    def _write_string(self, row, col, string, cell_format=None):
        str_error = 0

        # Check that row and col are valid and store max and min values.
        if self._check_dimensions(row, col):
            return -1

        # Check that the string is < 32767 chars.
        if len(string) > self.xls_strmax:
            string = string[: self.xls_strmax]
            str_error = -2

        # Write a shared string or an in-line string in constant_memory mode.
        if not self.constant_memory:
            string_index = self.str_table._get_shared_string_index(string)
        else:
            string_index = string

        # Write previous row if in in-line string constant_memory mode.
        if self.constant_memory and row > self.previous_row:
            self._write_single_row(row)

        # Store the cell data in the worksheet data table.
        self.table[row][col] = cell_string_tuple(string_index, cell_format)

        return str_error

    @convert_cell_args
    def write_number(self, row, col, number, cell_format=None):
        """
        Write a number to a worksheet cell.

        Args:
            row:         The cell row (zero indexed).
            col:         The cell column (zero indexed).
            number:      Cell data. Int or float.
            cell_format: An optional cell Format object.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.

        """
        return self._write_number(row, col, number, cell_format)

    # Undecorated version of write_number().
    def _write_number(self, row, col, number, cell_format=None):
        if isnan(number) or isinf(number):
            if self.nan_inf_to_errors:
                if isnan(number):
                    return self._write_formula(row, col, "#NUM!", cell_format, "#NUM!")
                elif number == math.inf:
                    return self._write_formula(row, col, "1/0", cell_format, "#DIV/0!")
                elif number == -math.inf:
                    return self._write_formula(row, col, "-1/0", cell_format, "#DIV/0!")
            else:
                raise TypeError(
                    "NAN/INF not supported in write_number() "
                    "without 'nan_inf_to_errors' Workbook() option"
                )

        # Check that row and col are valid and store max and min values.
        if self._check_dimensions(row, col):
            return -1

        # Write previous row if in in-line string constant_memory mode.
        if self.constant_memory and row > self.previous_row:
            self._write_single_row(row)

        # Store the cell data in the worksheet data table.
        self.table[row][col] = cell_number_tuple(number, cell_format)

        return 0

    @convert_cell_args
    def write_blank(self, row, col, blank, cell_format=None):
        """
        Write a blank cell with formatting to a worksheet cell. The blank
        token is ignored and the format only is written to the cell.

        Args:
            row:         The cell row (zero indexed).
            col:         The cell column (zero indexed).
            blank:       Any value. It is ignored.
            cell_format: An optional cell Format object.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.

        """
        return self._write_blank(row, col, blank, cell_format)

    # Undecorated version of write_blank().
    def _write_blank(self, row, col, blank, cell_format=None):
        # Don't write a blank cell unless it has a format.
        if cell_format is None:
            return 0

        # Check that row and col are valid and store max and min values.
        if self._check_dimensions(row, col):
            return -1

        # Write previous row if in in-line string constant_memory mode.
        if self.constant_memory and row > self.previous_row:
            self._write_single_row(row)

        # Store the cell data in the worksheet data table.
        self.table[row][col] = cell_blank_tuple(cell_format)

        return 0

    @convert_cell_args
    def write_formula(self, row, col, formula, cell_format=None, value=0):
        """
        Write a formula to a worksheet cell.

        Args:
            row:         The cell row (zero indexed).
            col:         The cell column (zero indexed).
            formula:     Cell formula.
            cell_format: An optional cell Format object.
            value:       An optional value for the formula. Default is 0.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.
            -2: Formula can't be None or empty.

        """
        # Check that row and col are valid and store max and min values.
        return self._write_formula(row, col, formula, cell_format, value)

    # Undecorated version of write_formula().
    def _write_formula(self, row, col, formula, cell_format=None, value=0):
        if self._check_dimensions(row, col):
            return -1

        if formula is None or formula == "":
            warn("Formula can't be None or empty")
            return -1

        # Check for dynamic array functions.
        if re_dynamic_function.search(formula):
            return self.write_dynamic_array_formula(
                row, col, row, col, formula, cell_format, value
            )

        # Hand off array formulas.
        if formula.startswith("{") and formula.endswith("}"):
            return self._write_array_formula(
                row, col, row, col, formula, cell_format, value
            )

        # Modify the formula string, as needed.
        formula = self._prepare_formula(formula)

        # Write previous row if in in-line string constant_memory mode.
        if self.constant_memory and row > self.previous_row:
            self._write_single_row(row)

        # Store the cell data in the worksheet data table.
        self.table[row][col] = cell_formula_tuple(formula, cell_format, value)

        return 0

    @convert_range_args
    def write_array_formula(
        self,
        first_row,
        first_col,
        last_row,
        last_col,
        formula,
        cell_format=None,
        value=0,
    ):
        """
        Write a formula to a worksheet cell/range.

        Args:
            first_row:    The first row of the cell range. (zero indexed).
            first_col:    The first column of the cell range.
            last_row:     The last row of the cell range. (zero indexed).
            last_col:     The last column of the cell range.
            formula:      Cell formula.
            cell_format:  An optional cell Format object.
            value:        An optional value for the formula. Default is 0.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.

        """
        # Check for dynamic array functions.
        if re_dynamic_function.search(formula):
            return self.write_dynamic_array_formula(
                first_row, first_col, last_row, last_col, formula, cell_format, value
            )

        return self._write_array_formula(
            first_row,
            first_col,
            last_row,
            last_col,
            formula,
            cell_format,
            value,
            "static",
        )

    @convert_range_args
    def write_dynamic_array_formula(
        self,
        first_row,
        first_col,
        last_row,
        last_col,
        formula,
        cell_format=None,
        value=0,
    ):
        """
        Write a dynamic array formula to a worksheet cell/range.

        Args:
            first_row:    The first row of the cell range. (zero indexed).
            first_col:    The first column of the cell range.
            last_row:     The last row of the cell range. (zero indexed).
            last_col:     The last column of the cell range.
            formula:      Cell formula.
            cell_format:  An optional cell Format object.
            value:        An optional value for the formula. Default is 0.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.

        """
        error = self._write_array_formula(
            first_row,
            first_col,
            last_row,
            last_col,
            formula,
            cell_format,
            value,
            "dynamic",
        )

        if error == 0:
            self.has_dynamic_arrays = True

        return error

    # Utility method to strip equal sign and array braces from a formula and
    # also expand out future and dynamic array formulas.
    def _prepare_formula(self, formula, expand_future_functions=False):
        # Remove array formula braces and the leading =.
        if formula.startswith("{"):
            formula = formula[1:]
        if formula.startswith("="):
            formula = formula[1:]
        if formula.endswith("}"):
            formula = formula[:-1]

        # Check if formula is already expanded by the user.
        if "_xlfn." in formula:
            return formula

        # Expand dynamic formulas.
        formula = re.sub(r"\bANCHORARRAY\(", "_xlfn.ANCHORARRAY(", formula)
        formula = re.sub(r"\bBYCOL\(", "_xlfn.BYCOL(", formula)
        formula = re.sub(r"\bBYROW\(", "_xlfn.BYROW(", formula)
        formula = re.sub(r"\bCHOOSECOLS\(", "_xlfn.CHOOSECOLS(", formula)
        formula = re.sub(r"\bCHOOSEROWS\(", "_xlfn.CHOOSEROWS(", formula)
        formula = re.sub(r"\bDROP\(", "_xlfn.DROP(", formula)
        formula = re.sub(r"\bEXPAND\(", "_xlfn.EXPAND(", formula)
        formula = re.sub(r"\bFILTER\(", "_xlfn._xlws.FILTER(", formula)
        formula = re.sub(r"\bHSTACK\(", "_xlfn.HSTACK(", formula)
        formula = re.sub(r"\bLAMBDA\(", "_xlfn.LAMBDA(", formula)
        formula = re.sub(r"\bMAKEARRAY\(", "_xlfn.MAKEARRAY(", formula)
        formula = re.sub(r"\bMAP\(", "_xlfn.MAP(", formula)
        formula = re.sub(r"\bRANDARRAY\(", "_xlfn.RANDARRAY(", formula)
        formula = re.sub(r"\bREDUCE\(", "_xlfn.REDUCE(", formula)
        formula = re.sub(r"\bSCAN\(", "_xlfn.SCAN(", formula)
        formula = re.sub(r"\SINGLE\(", "_xlfn.SINGLE(", formula)
        formula = re.sub(r"\bSEQUENCE\(", "_xlfn.SEQUENCE(", formula)
        formula = re.sub(r"\bSORT\(", "_xlfn._xlws.SORT(", formula)
        formula = re.sub(r"\bSORTBY\(", "_xlfn.SORTBY(", formula)
        formula = re.sub(r"\bSWITCH\(", "_xlfn.SWITCH(", formula)
        formula = re.sub(r"\bTAKE\(", "_xlfn.TAKE(", formula)
        formula = re.sub(r"\bTEXTSPLIT\(", "_xlfn.TEXTSPLIT(", formula)
        formula = re.sub(r"\bTOCOL\(", "_xlfn.TOCOL(", formula)
        formula = re.sub(r"\bTOROW\(", "_xlfn.TOROW(", formula)
        formula = re.sub(r"\bUNIQUE\(", "_xlfn.UNIQUE(", formula)
        formula = re.sub(r"\bVSTACK\(", "_xlfn.VSTACK(", formula)
        formula = re.sub(r"\bWRAPCOLS\(", "_xlfn.WRAPCOLS(", formula)
        formula = re.sub(r"\bWRAPROWS\(", "_xlfn.WRAPROWS(", formula)
        formula = re.sub(r"\bXLOOKUP\(", "_xlfn.XLOOKUP(", formula)

        if not self.use_future_functions and not expand_future_functions:
            return formula

        formula = re.sub(r"\bACOTH\(", "_xlfn.ACOTH(", formula)
        formula = re.sub(r"\bACOT\(", "_xlfn.ACOT(", formula)
        formula = re.sub(r"\bAGGREGATE\(", "_xlfn.AGGREGATE(", formula)
        formula = re.sub(r"\bARABIC\(", "_xlfn.ARABIC(", formula)
        formula = re.sub(r"\bARRAYTOTEXT\(", "_xlfn.ARRAYTOTEXT(", formula)
        formula = re.sub(r"\bBASE\(", "_xlfn.BASE(", formula)
        formula = re.sub(r"\bBETA.DIST\(", "_xlfn.BETA.DIST(", formula)
        formula = re.sub(r"\bBETA.INV\(", "_xlfn.BETA.INV(", formula)
        formula = re.sub(r"\bBINOM.DIST.RANGE\(", "_xlfn.BINOM.DIST.RANGE(", formula)
        formula = re.sub(r"\bBINOM.DIST\(", "_xlfn.BINOM.DIST(", formula)
        formula = re.sub(r"\bBINOM.INV\(", "_xlfn.BINOM.INV(", formula)
        formula = re.sub(r"\bBITAND\(", "_xlfn.BITAND(", formula)
        formula = re.sub(r"\bBITLSHIFT\(", "_xlfn.BITLSHIFT(", formula)
        formula = re.sub(r"\bBITOR\(", "_xlfn.BITOR(", formula)
        formula = re.sub(r"\bBITRSHIFT\(", "_xlfn.BITRSHIFT(", formula)
        formula = re.sub(r"\bBITXOR\(", "_xlfn.BITXOR(", formula)
        formula = re.sub(r"\bCEILING.MATH\(", "_xlfn.CEILING.MATH(", formula)
        formula = re.sub(r"\bCEILING.PRECISE\(", "_xlfn.CEILING.PRECISE(", formula)
        formula = re.sub(r"\bCHISQ.DIST.RT\(", "_xlfn.CHISQ.DIST.RT(", formula)
        formula = re.sub(r"\bCHISQ.DIST\(", "_xlfn.CHISQ.DIST(", formula)
        formula = re.sub(r"\bCHISQ.INV.RT\(", "_xlfn.CHISQ.INV.RT(", formula)
        formula = re.sub(r"\bCHISQ.INV\(", "_xlfn.CHISQ.INV(", formula)
        formula = re.sub(r"\bCHISQ.TEST\(", "_xlfn.CHISQ.TEST(", formula)
        formula = re.sub(r"\bCOMBINA\(", "_xlfn.COMBINA(", formula)
        formula = re.sub(r"\bCONCAT\(", "_xlfn.CONCAT(", formula)
        formula = re.sub(r"\bCONFIDENCE.NORM\(", "_xlfn.CONFIDENCE.NORM(", formula)
        formula = re.sub(r"\bCONFIDENCE.T\(", "_xlfn.CONFIDENCE.T(", formula)
        formula = re.sub(r"\bCOTH\(", "_xlfn.COTH(", formula)
        formula = re.sub(r"\bCOT\(", "_xlfn.COT(", formula)
        formula = re.sub(r"\bCOVARIANCE.P\(", "_xlfn.COVARIANCE.P(", formula)
        formula = re.sub(r"\bCOVARIANCE.S\(", "_xlfn.COVARIANCE.S(", formula)
        formula = re.sub(r"\bCSCH\(", "_xlfn.CSCH(", formula)
        formula = re.sub(r"\bCSC\(", "_xlfn.CSC(", formula)
        formula = re.sub(r"\bDAYS\(", "_xlfn.DAYS(", formula)
        formula = re.sub(r"\bDECIMAL\(", "_xlfn.DECIMAL(", formula)
        formula = re.sub(r"\bERF.PRECISE\(", "_xlfn.ERF.PRECISE(", formula)
        formula = re.sub(r"\bERFC.PRECISE\(", "_xlfn.ERFC.PRECISE(", formula)
        formula = re.sub(r"\bEXPON.DIST\(", "_xlfn.EXPON.DIST(", formula)
        formula = re.sub(r"\bF.DIST.RT\(", "_xlfn.F.DIST.RT(", formula)
        formula = re.sub(r"\bF.DIST\(", "_xlfn.F.DIST(", formula)
        formula = re.sub(r"\bF.INV.RT\(", "_xlfn.F.INV.RT(", formula)
        formula = re.sub(r"\bF.INV\(", "_xlfn.F.INV(", formula)
        formula = re.sub(r"\bF.TEST\(", "_xlfn.F.TEST(", formula)
        formula = re.sub(r"\bFILTERXML\(", "_xlfn.FILTERXML(", formula)
        formula = re.sub(r"\bFLOOR.MATH\(", "_xlfn.FLOOR.MATH(", formula)
        formula = re.sub(r"\bFLOOR.PRECISE\(", "_xlfn.FLOOR.PRECISE(", formula)
        formula = re.sub(
            r"\bFORECAST.ETS.CONFINT\(", "_xlfn.FORECAST.ETS.CONFINT(", formula
        )
        formula = re.sub(
            r"\bFORECAST.ETS.SEASONALITY\(", "_xlfn.FORECAST.ETS.SEASONALITY(", formula
        )
        formula = re.sub(r"\bFORECAST.ETS.STAT\(", "_xlfn.FORECAST.ETS.STAT(", formula)
        formula = re.sub(r"\bFORECAST.ETS\(", "_xlfn.FORECAST.ETS(", formula)
        formula = re.sub(r"\bFORECAST.LINEAR\(", "_xlfn.FORECAST.LINEAR(", formula)
        formula = re.sub(r"\bFORMULATEXT\(", "_xlfn.FORMULATEXT(", formula)
        formula = re.sub(r"\bGAMMA.DIST\(", "_xlfn.GAMMA.DIST(", formula)
        formula = re.sub(r"\bGAMMA.INV\(", "_xlfn.GAMMA.INV(", formula)
        formula = re.sub(r"\bGAMMALN.PRECISE\(", "_xlfn.GAMMALN.PRECISE(", formula)
        formula = re.sub(r"\bGAMMA\(", "_xlfn.GAMMA(", formula)
        formula = re.sub(r"\bGAUSS\(", "_xlfn.GAUSS(", formula)
        formula = re.sub(r"\bHYPGEOM.DIST\(", "_xlfn.HYPGEOM.DIST(", formula)
        formula = re.sub(r"\bIFNA\(", "_xlfn.IFNA(", formula)
        formula = re.sub(r"\bIFS\(", "_xlfn.IFS(", formula)
        formula = re.sub(r"\bIMAGE\(", "_xlfn.IMAGE(", formula)
        formula = re.sub(r"\bIMCOSH\(", "_xlfn.IMCOSH(", formula)
        formula = re.sub(r"\bIMCOT\(", "_xlfn.IMCOT(", formula)
        formula = re.sub(r"\bIMCSCH\(", "_xlfn.IMCSCH(", formula)
        formula = re.sub(r"\bIMCSC\(", "_xlfn.IMCSC(", formula)
        formula = re.sub(r"\bIMSECH\(", "_xlfn.IMSECH(", formula)
        formula = re.sub(r"\bIMSEC\(", "_xlfn.IMSEC(", formula)
        formula = re.sub(r"\bIMSINH\(", "_xlfn.IMSINH(", formula)
        formula = re.sub(r"\bIMTAN\(", "_xlfn.IMTAN(", formula)
        formula = re.sub(r"\bISFORMULA\(", "_xlfn.ISFORMULA(", formula)
        formula = re.sub(r"\bISOMITTED\(", "_xlfn.ISOMITTED(", formula)
        formula = re.sub(r"\bISOWEEKNUM\(", "_xlfn.ISOWEEKNUM(", formula)
        formula = re.sub(r"\bLET\(", "_xlfn.LET(", formula)
        formula = re.sub(r"\bLOGNORM.DIST\(", "_xlfn.LOGNORM.DIST(", formula)
        formula = re.sub(r"\bLOGNORM.INV\(", "_xlfn.LOGNORM.INV(", formula)
        formula = re.sub(r"\bMAXIFS\(", "_xlfn.MAXIFS(", formula)
        formula = re.sub(r"\bMINIFS\(", "_xlfn.MINIFS(", formula)
        formula = re.sub(r"\bMODE.MULT\(", "_xlfn.MODE.MULT(", formula)
        formula = re.sub(r"\bMODE.SNGL\(", "_xlfn.MODE.SNGL(", formula)
        formula = re.sub(r"\bMUNIT\(", "_xlfn.MUNIT(", formula)
        formula = re.sub(r"\bNEGBINOM.DIST\(", "_xlfn.NEGBINOM.DIST(", formula)
        formula = re.sub(r"\bNORM.DIST\(", "_xlfn.NORM.DIST(", formula)
        formula = re.sub(r"\bNORM.INV\(", "_xlfn.NORM.INV(", formula)
        formula = re.sub(r"\bNORM.S.DIST\(", "_xlfn.NORM.S.DIST(", formula)
        formula = re.sub(r"\bNORM.S.INV\(", "_xlfn.NORM.S.INV(", formula)
        formula = re.sub(r"\bNUMBERVALUE\(", "_xlfn.NUMBERVALUE(", formula)
        formula = re.sub(r"\bPDURATION\(", "_xlfn.PDURATION(", formula)
        formula = re.sub(r"\bPERCENTILE.EXC\(", "_xlfn.PERCENTILE.EXC(", formula)
        formula = re.sub(r"\bPERCENTILE.INC\(", "_xlfn.PERCENTILE.INC(", formula)
        formula = re.sub(r"\bPERCENTRANK.EXC\(", "_xlfn.PERCENTRANK.EXC(", formula)
        formula = re.sub(r"\bPERCENTRANK.INC\(", "_xlfn.PERCENTRANK.INC(", formula)
        formula = re.sub(r"\bPERMUTATIONA\(", "_xlfn.PERMUTATIONA(", formula)
        formula = re.sub(r"\bPHI\(", "_xlfn.PHI(", formula)
        formula = re.sub(r"\bPOISSON.DIST\(", "_xlfn.POISSON.DIST(", formula)
        formula = re.sub(r"\bQUARTILE.EXC\(", "_xlfn.QUARTILE.EXC(", formula)
        formula = re.sub(r"\bQUARTILE.INC\(", "_xlfn.QUARTILE.INC(", formula)
        formula = re.sub(r"\bQUERYSTRING\(", "_xlfn.QUERYSTRING(", formula)
        formula = re.sub(r"\bRANK.AVG\(", "_xlfn.RANK.AVG(", formula)
        formula = re.sub(r"\bRANK.EQ\(", "_xlfn.RANK.EQ(", formula)
        formula = re.sub(r"\bRRI\(", "_xlfn.RRI(", formula)
        formula = re.sub(r"\bSECH\(", "_xlfn.SECH(", formula)
        formula = re.sub(r"\bSEC\(", "_xlfn.SEC(", formula)
        formula = re.sub(r"\bSHEETS\(", "_xlfn.SHEETS(", formula)
        formula = re.sub(r"\bSHEET\(", "_xlfn.SHEET(", formula)
        formula = re.sub(r"\bSKEW.P\(", "_xlfn.SKEW.P(", formula)
        formula = re.sub(r"\bSTDEV.P\(", "_xlfn.STDEV.P(", formula)
        formula = re.sub(r"\bSTDEV.S\(", "_xlfn.STDEV.S(", formula)
        formula = re.sub(r"\bT.DIST.2T\(", "_xlfn.T.DIST.2T(", formula)
        formula = re.sub(r"\bT.DIST.RT\(", "_xlfn.T.DIST.RT(", formula)
        formula = re.sub(r"\bT.DIST\(", "_xlfn.T.DIST(", formula)
        formula = re.sub(r"\bT.INV.2T\(", "_xlfn.T.INV.2T(", formula)
        formula = re.sub(r"\bT.INV\(", "_xlfn.T.INV(", formula)
        formula = re.sub(r"\bT.TEST\(", "_xlfn.T.TEST(", formula)
        formula = re.sub(r"\bTEXTAFTER\(", "_xlfn.TEXTAFTER(", formula)
        formula = re.sub(r"\bTEXTBEFORE\(", "_xlfn.TEXTBEFORE(", formula)
        formula = re.sub(r"\bTEXTJOIN\(", "_xlfn.TEXTJOIN(", formula)
        formula = re.sub(r"\bUNICHAR\(", "_xlfn.UNICHAR(", formula)
        formula = re.sub(r"\bUNICODE\(", "_xlfn.UNICODE(", formula)
        formula = re.sub(r"\bVALUETOTEXT\(", "_xlfn.VALUETOTEXT(", formula)
        formula = re.sub(r"\bVAR.P\(", "_xlfn.VAR.P(", formula)
        formula = re.sub(r"\bVAR.S\(", "_xlfn.VAR.S(", formula)
        formula = re.sub(r"\bWEBSERVICE\(", "_xlfn.WEBSERVICE(", formula)
        formula = re.sub(r"\bWEIBULL.DIST\(", "_xlfn.WEIBULL.DIST(", formula)
        formula = re.sub(r"\bXMATCH\(", "_xlfn.XMATCH(", formula)
        formula = re.sub(r"\bXOR\(", "_xlfn.XOR(", formula)
        formula = re.sub(r"\bZ.TEST\(", "_xlfn.Z.TEST(", formula)

        return formula

    # Undecorated version of write_array_formula() and
    # write_dynamic_array_formula().
    def _write_array_formula(
        self,
        first_row,
        first_col,
        last_row,
        last_col,
        formula,
        cell_format=None,
        value=0,
        atype="static",
    ):
        # Swap last row/col with first row/col as necessary.
        if first_row > last_row:
            first_row, last_row = last_row, first_row
        if first_col > last_col:
            first_col, last_col = last_col, first_col

        # Check that row and col are valid and store max and min values.
        if self._check_dimensions(first_row, first_col):
            return -1
        if self._check_dimensions(last_row, last_col):
            return -1

        # Define array range
        if first_row == last_row and first_col == last_col:
            cell_range = xl_rowcol_to_cell(first_row, first_col)
        else:
            cell_range = (
                xl_rowcol_to_cell(first_row, first_col)
                + ":"
                + xl_rowcol_to_cell(last_row, last_col)
            )

        # Modify the formula string, as needed.
        formula = self._prepare_formula(formula)

        # Write previous row if in in-line string constant_memory mode.
        if self.constant_memory and first_row > self.previous_row:
            self._write_single_row(first_row)

        # Store the cell data in the worksheet data table.
        self.table[first_row][first_col] = cell_arformula_tuple(
            formula, cell_format, value, cell_range, atype
        )

        # Pad out the rest of the area with formatted zeroes.
        if not self.constant_memory:
            for row in range(first_row, last_row + 1):
                for col in range(first_col, last_col + 1):
                    if row != first_row or col != first_col:
                        self._write_number(row, col, 0, cell_format)

        return 0

    @convert_cell_args
    def write_datetime(self, row, col, date, cell_format=None):
        """
        Write a date or time to a worksheet cell.

        Args:
            row:         The cell row (zero indexed).
            col:         The cell column (zero indexed).
            date:        Date and/or time as a datetime object.
            cell_format: A cell Format object.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.

        """
        return self._write_datetime(row, col, date, cell_format)

    # Undecorated version of write_datetime().
    def _write_datetime(self, row, col, date, cell_format=None):
        # Check that row and col are valid and store max and min values.
        if self._check_dimensions(row, col):
            return -1

        # Write previous row if in in-line string constant_memory mode.
        if self.constant_memory and row > self.previous_row:
            self._write_single_row(row)

        # Convert datetime to an Excel date.
        number = self._convert_date_time(date)

        # Add the default date format.
        if cell_format is None:
            cell_format = self.default_date_format

        # Store the cell data in the worksheet data table.
        self.table[row][col] = cell_datetime_tuple(number, cell_format)

        return 0

    @convert_cell_args
    def write_boolean(self, row, col, boolean, cell_format=None):
        """
        Write a boolean value to a worksheet cell.

        Args:
            row:         The cell row (zero indexed).
            col:         The cell column (zero indexed).
            boolean:     Cell data. bool type.
            cell_format: An optional cell Format object.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.

        """
        return self._write_boolean(row, col, boolean, cell_format)

    # Undecorated version of write_boolean().
    def _write_boolean(self, row, col, boolean, cell_format=None):
        # Check that row and col are valid and store max and min values.
        if self._check_dimensions(row, col):
            return -1

        # Write previous row if in in-line string constant_memory mode.
        if self.constant_memory and row > self.previous_row:
            self._write_single_row(row)

        if boolean:
            value = 1
        else:
            value = 0

        # Store the cell data in the worksheet data table.
        self.table[row][col] = cell_boolean_tuple(value, cell_format)

        return 0

    # Write a hyperlink. This is comprised of two elements: the displayed
    # string and the non-displayed link. The displayed string is the same as
    # the link unless an alternative string is specified. The display string
    # is written using the write_string() method. Therefore the max characters
    # string limit applies.
    #
    # The hyperlink can be to a http, ftp, mail, internal sheet, or external
    # directory urls.
    @convert_cell_args
    def write_url(self, row, col, url, cell_format=None, string=None, tip=None):
        """
        Write a hyperlink to a worksheet cell.

        Args:
            row:    The cell row (zero indexed).
            col:    The cell column (zero indexed).
            url:    Hyperlink url.
            format: An optional cell Format object.
            string: An optional display string for the hyperlink.
            tip:    An optional tooltip.
        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.
            -2: String longer than 32767 characters.
            -3: URL longer than Excel limit of 255 characters.
            -4: Exceeds Excel limit of 65,530 urls per worksheet.
        """
        return self._write_url(row, col, url, cell_format, string, tip)

    # Undecorated version of write_url().
    def _write_url(self, row, col, url, cell_format=None, string=None, tip=None):
        # Check that row and col are valid and store max and min values
        if self._check_dimensions(row, col):
            return -1

        # Set the displayed string to the URL unless defined by the user.
        if string is None:
            string = url

        # Default to external link type such as 'http://' or 'external:'.
        link_type = 1

        # Remove the URI scheme from internal links.
        if url.startswith("internal:"):
            url = url.replace("internal:", "")
            string = string.replace("internal:", "")
            link_type = 2

        # Remove the URI scheme from external links and change the directory
        # separator from Unix to Dos.
        external = False
        if url.startswith("external:"):
            url = url.replace("external:", "")
            url = url.replace("/", "\\")
            string = string.replace("external:", "")
            string = string.replace("/", "\\")
            external = True

        # Strip the mailto header.
        string = string.replace("mailto:", "")

        # Check that the string is < 32767 chars
        str_error = 0
        if len(string) > self.xls_strmax:
            warn(
                "Ignoring URL since it exceeds Excel's string limit of "
                "32767 characters"
            )
            return -2

        # Copy string for use in hyperlink elements.
        url_str = string

        # External links to URLs and to other Excel workbooks have slightly
        # different characteristics that we have to account for.
        if link_type == 1:
            # Split url into the link and optional anchor/location.
            if "#" in url:
                url, url_str = url.split("#", 1)
            else:
                url_str = None

            url = self._escape_url(url)

            if url_str is not None and not external:
                url_str = self._escape_url(url_str)

            # Add the file:/// URI to the url for Windows style "C:/" link and
            # Network shares.
            if re.match(r"\w:", url) or re.match(r"\\", url):
                url = "file:///" + url

            # Convert a .\dir\file.xlsx link to dir\file.xlsx.
            url = re.sub(r"^\.\\", "", url)

        # Excel limits the escaped URL and location/anchor to 255 characters.
        tmp_url_str = url_str or ""
        max_url = self.max_url_length
        if len(url) > max_url or len(tmp_url_str) > max_url:
            warn(
                "Ignoring URL '%s' with link or location/anchor > %d "
                "characters since it exceeds Excel's limit for URLS" % (url, max_url)
            )
            return -3

        # Check the limit of URLS per worksheet.
        self.hlink_count += 1

        if self.hlink_count > 65530:
            warn(
                "Ignoring URL '%s' since it exceeds Excel's limit of "
                "65,530 URLS per worksheet." % url
            )
            return -4

        # Write previous row if in in-line string constant_memory mode.
        if self.constant_memory and row > self.previous_row:
            self._write_single_row(row)

        # Add the default URL format.
        if cell_format is None:
            cell_format = self.default_url_format

        # Write the hyperlink string.
        self._write_string(row, col, string, cell_format)

        # Store the hyperlink data in a separate structure.
        self.hyperlinks[row][col] = {
            "link_type": link_type,
            "url": url,
            "str": url_str,
            "tip": tip,
        }

        return str_error

    @convert_cell_args
    def write_rich_string(self, row, col, *args):
        """
        Write a "rich" string with multiple formats to a worksheet cell.

        Args:
            row:          The cell row (zero indexed).
            col:          The cell column (zero indexed).
            string_parts: String and format pairs.
            cell_format:  Optional Format object.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.
            -2: String truncated to 32k characters.
            -3: 2 consecutive formats used.
            -4: Empty string used.
            -5: Insufficient parameters.

        """

        return self._write_rich_string(row, col, *args)

    # Undecorated version of write_rich_string().
    def _write_rich_string(self, row, col, *args):
        tokens = list(args)
        cell_format = None
        string_index = 0
        raw_string = ""

        # Check that row and col are valid and store max and min values
        if self._check_dimensions(row, col):
            return -1

        # If the last arg is a format we use it as the cell format.
        if isinstance(tokens[-1], Format):
            cell_format = tokens.pop()

        # Create a temp XMLWriter object and use it to write the rich string
        # XML to a string.
        fh = StringIO()
        self.rstring = XMLwriter()
        self.rstring._set_filehandle(fh)

        # Create a temp format with the default font for unformatted fragments.
        default = Format()

        # Convert list of format, string tokens to pairs of (format, string)
        # except for the first string fragment which doesn't require a default
        # formatting run. Use the default for strings without a leading format.
        fragments = []
        previous = "format"
        pos = 0

        if len(tokens) <= 2:
            warn(
                "You must specify more than 2 format/fragments for rich "
                "strings. Ignoring input in write_rich_string()."
            )
            return -5

        for token in tokens:
            if not isinstance(token, Format):
                # Token is a string.
                if previous != "format":
                    # If previous token wasn't a format add one before string.
                    fragments.append(default)
                    fragments.append(token)
                else:
                    # If previous token was a format just add the string.
                    fragments.append(token)

                if token == "":
                    warn(
                        "Excel doesn't allow empty strings in rich strings. "
                        "Ignoring input in write_rich_string()."
                    )
                    return -4

                # Keep track of unformatted string.
                raw_string += token
                previous = "string"
            else:
                # Can't allow 2 formats in a row.
                if previous == "format" and pos > 0:
                    warn(
                        "Excel doesn't allow 2 consecutive formats in rich "
                        "strings. Ignoring input in write_rich_string()."
                    )
                    return -3

                # Token is a format object. Add it to the fragment list.
                fragments.append(token)
                previous = "format"

            pos += 1

        # If the first token is a string start the <r> element.
        if not isinstance(fragments[0], Format):
            self.rstring._xml_start_tag("r")

        # Write the XML elements for the $format $string fragments.
        for token in fragments:
            if isinstance(token, Format):
                # Write the font run.
                self.rstring._xml_start_tag("r")
                self._write_font(token)
            else:
                # Write the string fragment part, with whitespace handling.
                attributes = []

                if preserve_whitespace(token):
                    attributes.append(("xml:space", "preserve"))

                self.rstring._xml_data_element("t", token, attributes)
                self.rstring._xml_end_tag("r")

        # Read the in-memory string.
        string = self.rstring.fh.getvalue()

        # Check that the string is < 32767 chars.
        if len(raw_string) > self.xls_strmax:
            warn(
                "String length must be less than or equal to Excel's limit "
                "of 32,767 characters in write_rich_string()."
            )
            return -2

        # Write a shared string or an in-line string in constant_memory mode.
        if not self.constant_memory:
            string_index = self.str_table._get_shared_string_index(string)
        else:
            string_index = string

        # Write previous row if in in-line string constant_memory mode.
        if self.constant_memory and row > self.previous_row:
            self._write_single_row(row)

        # Store the cell data in the worksheet data table.
        self.table[row][col] = cell_rich_string_tuple(
            string_index, cell_format, raw_string
        )

        return 0

    def add_write_handler(self, user_type, user_function):
        """
        Add a callback function to the write() method to handle user defined
        types.

        Args:
            user_type:      The user type() to match on.
            user_function:  The user defined function to write the type data.
        Returns:
            Nothing.

        """

        self.write_handlers[user_type] = user_function

    @convert_cell_args
    def write_row(self, row, col, data, cell_format=None):
        """
        Write a row of data starting from (row, col).

        Args:
            row:    The cell row (zero indexed).
            col:    The cell column (zero indexed).
            data:   A list of tokens to be written with write().
            format: An optional cell Format object.
        Returns:
            0:  Success.
            other: Return value of write() method.

        """
        for token in data:
            error = self._write(row, col, token, cell_format)
            if error:
                return error
            col += 1

        return 0

    @convert_cell_args
    def write_column(self, row, col, data, cell_format=None):
        """
        Write a column of data starting from (row, col).

        Args:
            row:    The cell row (zero indexed).
            col:    The cell column (zero indexed).
            data:   A list of tokens to be written with write().
            format: An optional cell Format object.
        Returns:
            0:  Success.
            other: Return value of write() method.

        """
        for token in data:
            error = self._write(row, col, token, cell_format)
            if error:
                return error
            row += 1

        return 0

    @convert_cell_args
    def insert_image(self, row, col, filename, options=None):
        """
        Insert an image with its top-left corner in a worksheet cell.

        Args:
            row:      The cell row (zero indexed).
            col:      The cell column (zero indexed).
            filename: Path and filename for in supported formats.
            options:  Position, scale, url and data stream of the image.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.

        """
        # Check insert (row, col) without storing.
        if self._check_dimensions(row, col, True, True):
            warn("Cannot insert image at (%d, %d)." % (row, col))
            return -1

        if options is None:
            options = {}

        x_offset = options.get("x_offset", 0)
        y_offset = options.get("y_offset", 0)
        x_scale = options.get("x_scale", 1)
        y_scale = options.get("y_scale", 1)
        url = options.get("url", None)
        tip = options.get("tip", None)
        anchor = options.get("object_position", 2)
        image_data = options.get("image_data", None)
        description = options.get("description", None)
        decorative = options.get("decorative", False)

        # For backward compatibility with older parameter name.
        anchor = options.get("positioning", anchor)

        if not image_data and not os.path.exists(filename):
            warn("Image file '%s' not found." % filename)
            return -1

        self.images.append(
            [
                row,
                col,
                filename,
                x_offset,
                y_offset,
                x_scale,
                y_scale,
                url,
                tip,
                anchor,
                image_data,
                description,
                decorative,
            ]
        )
        return 0

    @convert_cell_args
    def insert_textbox(self, row, col, text, options=None):
        """
        Insert an textbox with its top-left corner in a worksheet cell.

        Args:
            row:      The cell row (zero indexed).
            col:      The cell column (zero indexed).
            text:     The text for the textbox.
            options:  Textbox options.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.

        """
        # Check insert (row, col) without storing.
        if self._check_dimensions(row, col, True, True):
            warn("Cannot insert textbox at (%d, %d)." % (row, col))
            return -1

        if text is None:
            text = ""

        if options is None:
            options = {}

        x_offset = options.get("x_offset", 0)
        y_offset = options.get("y_offset", 0)
        x_scale = options.get("x_scale", 1)
        y_scale = options.get("y_scale", 1)
        anchor = options.get("object_position", 1)
        description = options.get("description", None)
        decorative = options.get("decorative", False)

        self.shapes.append(
            [
                row,
                col,
                x_offset,
                y_offset,
                x_scale,
                y_scale,
                text,
                anchor,
                options,
                description,
                decorative,
            ]
        )
        return 0

    @convert_cell_args
    def insert_chart(self, row, col, chart, options=None):
        """
        Insert an chart with its top-left corner in a worksheet cell.

        Args:
            row:     The cell row (zero indexed).
            col:     The cell column (zero indexed).
            chart:   Chart object.
            options: Position and scale of the chart.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.

        """
        # Check insert (row, col) without storing.
        if self._check_dimensions(row, col, True, True):
            warn("Cannot insert chart at (%d, %d)." % (row, col))
            return -1

        if options is None:
            options = {}

        # Ensure a chart isn't inserted more than once.
        if chart.already_inserted or chart.combined and chart.combined.already_inserted:
            warn("Chart cannot be inserted in a worksheet more than once.")
            return
        else:
            chart.already_inserted = True

            if chart.combined:
                chart.combined.already_inserted = True

        x_offset = options.get("x_offset", 0)
        y_offset = options.get("y_offset", 0)
        x_scale = options.get("x_scale", 1)
        y_scale = options.get("y_scale", 1)
        anchor = options.get("object_position", 1)
        description = options.get("description", None)
        decorative = options.get("decorative", False)

        # Allow Chart to override the scale and offset.
        if chart.x_scale != 1:
            x_scale = chart.x_scale

        if chart.y_scale != 1:
            y_scale = chart.y_scale

        if chart.x_offset:
            x_offset = chart.x_offset

        if chart.y_offset:
            y_offset = chart.y_offset

        self.charts.append(
            [
                row,
                col,
                chart,
                x_offset,
                y_offset,
                x_scale,
                y_scale,
                anchor,
                description,
                decorative,
            ]
        )
        return 0

    @convert_cell_args
    def write_comment(self, row, col, comment, options=None):
        """
        Write a comment to a worksheet cell.

        Args:
            row:     The cell row (zero indexed).
            col:     The cell column (zero indexed).
            comment: Cell comment. Str.
            options: Comment formatting options.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.
            -2: String longer than 32k characters.

        """
        if options is None:
            options = {}

        # Check that row and col are valid and store max and min values
        if self._check_dimensions(row, col):
            return -1

        # Check that the comment string is < 32767 chars.
        if len(comment) > self.xls_strmax:
            return -2

        self.has_vml = 1
        self.has_comments = 1

        # Store the options of the cell comment, to process on file close.
        self.comments[row][col] = [row, col, comment, options]

        return 0

    def show_comments(self):
        """
        Make any comments in the worksheet visible.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.comments_visible = 1

    def set_background(self, filename, is_byte_stream=False):
        """
        Set a background image for a worksheet.

        Args:
            filename:       Path and filename for in supported formats.
            is_byte_stream: File is a stream of bytes.
        Returns:
            Nothing.

        """

        if not is_byte_stream and not os.path.exists(filename):
            warn("Image file '%s' not found." % filename)
            return -1

        self.background_bytes = is_byte_stream
        self.background_image = filename

    def set_comments_author(self, author):
        """
        Set the default author of the cell comments.

        Args:
            author: Comment author name. String.

        Returns:
            Nothing.

        """
        self.comments_author = author

    def get_name(self):
        """
        Retrieve the worksheet name.

        Args:
            None.

        Returns:
            Nothing.

        """
        # There is no set_name() method. Name must be set in add_worksheet().
        return self.name

    def activate(self):
        """
        Set this worksheet as the active worksheet, i.e. the worksheet that is
        displayed when the workbook is opened. Also set it as selected.

        Note: An active worksheet cannot be hidden.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.hidden = 0
        self.selected = 1
        self.worksheet_meta.activesheet = self.index

    def select(self):
        """
        Set current worksheet as a selected worksheet, i.e. the worksheet
        has its tab highlighted.

        Note: A selected worksheet cannot be hidden.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.selected = 1
        self.hidden = 0

    def hide(self):
        """
        Hide the current worksheet.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.hidden = 1

        # A hidden worksheet shouldn't be active or selected.
        self.selected = 0

    def very_hidden(self):
        """
        Hide the current worksheet. This can only be unhidden by VBA.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.hidden = 2

        # A hidden worksheet shouldn't be active or selected.
        self.selected = 0

    def set_first_sheet(self):
        """
        Set current worksheet as the first visible sheet. This is necessary
        when there are a large number of worksheets and the activated
        worksheet is not visible on the screen.

        Note: A selected worksheet cannot be hidden.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.hidden = 0  # Active worksheet can't be hidden.
        self.worksheet_meta.firstsheet = self.index

    @convert_column_args
    def set_column(
        self, first_col, last_col, width=None, cell_format=None, options=None
    ):
        """
        Set the width, and other properties of a single column or a
        range of columns.

        Args:
            first_col:   First column (zero-indexed).
            last_col:    Last column (zero-indexed). Can be same as first_col.
            width:       Column width. (optional).
            cell_format: Column cell_format. (optional).
            options:     Dict of options such as hidden and level.

        Returns:
            0:  Success.
            -1: Column number is out of worksheet bounds.

        """
        if options is None:
            options = {}

        # Ensure 2nd col is larger than first.
        if first_col > last_col:
            (first_col, last_col) = (last_col, first_col)

        # Don't modify the row dimensions when checking the columns.
        ignore_row = True

        # Set optional column values.
        hidden = options.get("hidden", False)
        collapsed = options.get("collapsed", False)
        level = options.get("level", 0)

        # Store the column dimension only in some conditions.
        if cell_format or (width and hidden):
            ignore_col = False
        else:
            ignore_col = True

        # Check that each column is valid and store the max and min values.
        if self._check_dimensions(0, last_col, ignore_row, ignore_col):
            return -1
        if self._check_dimensions(0, first_col, ignore_row, ignore_col):
            return -1

        # Set the limits for the outline levels (0 <= x <= 7).
        if level < 0:
            level = 0
        if level > 7:
            level = 7

        if level > self.outline_col_level:
            self.outline_col_level = level

        # Store the column data.
        for col in range(first_col, last_col + 1):
            self.col_info[col] = [width, cell_format, hidden, level, collapsed, False]

        # Store the column change to allow optimizations.
        self.col_size_changed = True

        return 0

    @convert_column_args
    def set_column_pixels(
        self, first_col, last_col, width=None, cell_format=None, options=None
    ):
        """
        Set the width, and other properties of a single column or a
        range of columns, where column width is in pixels.

        Args:
            first_col:   First column (zero-indexed).
            last_col:    Last column (zero-indexed). Can be same as first_col.
            width:       Column width in pixels. (optional).
            cell_format: Column cell_format. (optional).
            options:     Dict of options such as hidden and level.

        Returns:
            0:  Success.
            -1: Column number is out of worksheet bounds.

        """
        if width is not None:
            width = self._pixels_to_width(width)

        return self.set_column(first_col, last_col, width, cell_format, options)

    def autofit(self):
        """
        Simulate autofit based on the data, and datatypes in each column.

        Args:
            None.

        Returns:
            Nothing.

        """
        if self.constant_memory:
            warn("Autofit is not supported in constant_memory mode.")
            return

        # No data written to the target sheet; nothing to autofit
        if self.dim_rowmax is None:
            return

        # Store the max pixel width for each column.
        col_width_max = {}

        # Create a reverse lookup for the share strings table so we can convert
        # the string id back to the original string.
        strings = sorted(
            self.str_table.string_table, key=self.str_table.string_table.__getitem__
        )

        for row_num in range(self.dim_rowmin, self.dim_rowmax + 1):
            if not self.table.get(row_num):
                continue

            for col_num in range(self.dim_colmin, self.dim_colmax + 1):
                if col_num in self.table[row_num]:
                    cell = self.table[row_num][col_num]
                    cell_type = cell.__class__.__name__
                    length = 0

                    if cell_type in ("String", "RichString"):
                        # Handle strings and rich strings.
                        #
                        # For standard shared strings we do a reverse lookup
                        # from the shared string id to the actual string. For
                        # rich strings we use the unformatted string. We also
                        # split multi-line strings and handle each part
                        # separately.
                        if cell_type == "String":
                            string_id = cell.string
                            string = strings[string_id]
                        else:
                            string = cell.raw_string

                        if "\n" not in string:
                            # Single line string.
                            length = xl_pixel_width(string)
                        else:
                            # Handle multi-line strings.
                            for string in string.split("\n"):
                                seg_length = xl_pixel_width(string)
                                if seg_length > length:
                                    length = seg_length

                    elif cell_type == "Number":
                        # Handle numbers.
                        #
                        # We use a workaround/optimization for numbers since
                        # digits all have a pixel width of 7. This gives a
                        # slightly greater width for the decimal place and
                        # minus sign but only by a few pixels and
                        # over-estimation is okay.
                        length = 7 * len(str(cell.number))

                    elif cell_type == "Datetime":
                        # Handle dates.
                        #
                        # The following uses the default width for mm/dd/yyyy
                        # dates. It isn't feasible to parse the number format
                        # to get the actual string width for all format types.
                        length = self.default_date_pixels

                    elif cell_type == "Boolean":
                        # Handle boolean values.
                        #
                        # Use the Excel standard widths for TRUE and FALSE.
                        if cell.boolean:
                            length = 31
                        else:
                            length = 36

                    elif cell_type == "Formula" or cell_type == "ArrayFormula":
                        # Handle formulas.
                        #
                        # We only try to autofit a formula if it has a
                        # non-zero value.
                        if isinstance(cell.value, (float, int)):
                            if cell.value > 0:
                                length = 7 * len(str(cell.value))

                        elif isinstance(cell.value, str):
                            length = xl_pixel_width(cell.value)

                        elif isinstance(cell.value, bool):
                            if cell.value:
                                length = 31
                            else:
                                length = 36

                    # If the cell is in an autofilter header we add an
                    # additional 16 pixels for the dropdown arrow.
                    if self.filter_cells.get((row_num, col_num)) and length > 0:
                        length += 16

                    # Add the string length to the lookup table.
                    width_max = col_width_max.get(col_num, 0)
                    if length > width_max:
                        col_width_max[col_num] = length

        # Apply the width to the column.
        for col_num, pixel_width in col_width_max.items():
            # Convert the string pixel width to a character width using an
            # additional padding of 7 pixels, like Excel.
            width = self._pixels_to_width(pixel_width + 7)

            # The max column character width in Excel is 255.
            if width > 255.0:
                width = 255.0

            # Add the width to an existing col info structure or add a new one.
            if self.col_info.get(col_num):
                # We only update the width for an existing column if it is
                # greater than the user defined value. This allows the user
                # to pre-load a minimum col width.
                col_info = self.col_info.get(col_num)
                user_width = col_info[0]
                hidden = col_info[5]
                if user_width is not None and not hidden:
                    # Col info is user defined.
                    if width > user_width:
                        self.col_info[col_num][0] = width
                        self.col_info[col_num][5] = True
                else:
                    self.col_info[col_num][0] = width
                    self.col_info[col_num][5] = True
            else:
                self.col_info[col_num] = [width, None, False, 0, False, True]

    def set_row(self, row, height=None, cell_format=None, options=None):
        """
        Set the width, and other properties of a row.

        Args:
            row:         Row number (zero-indexed).
            height:      Row height. (optional).
            cell_format: Row cell_format. (optional).
            options:     Dict of options such as hidden, level and collapsed.

        Returns:
            0:  Success.
            -1: Row number is out of worksheet bounds.

        """
        if options is None:
            options = {}

        # Use minimum col in _check_dimensions().
        if self.dim_colmin is not None:
            min_col = self.dim_colmin
        else:
            min_col = 0

        # Check that row is valid.
        if self._check_dimensions(row, min_col):
            return -1

        if height is None:
            height = self.default_row_height

        # Set optional row values.
        hidden = options.get("hidden", False)
        collapsed = options.get("collapsed", False)
        level = options.get("level", 0)

        # If the height is 0 the row is hidden and the height is the default.
        if height == 0:
            hidden = 1
            height = self.default_row_height

        # Set the limits for the outline levels (0 <= x <= 7).
        if level < 0:
            level = 0
        if level > 7:
            level = 7

        if level > self.outline_row_level:
            self.outline_row_level = level

        # Store the row properties.
        self.set_rows[row] = [height, cell_format, hidden, level, collapsed]

        # Store the row change to allow optimizations.
        self.row_size_changed = True

        # Store the row sizes for use when calculating image vertices.
        self.row_sizes[row] = [height, hidden]

        return 0

    def set_row_pixels(self, row, height=None, cell_format=None, options=None):
        """
        Set the width (in pixels), and other properties of a row.

        Args:
            row:         Row number (zero-indexed).
            height:      Row height in pixels. (optional).
            cell_format: Row cell_format. (optional).
            options:     Dict of options such as hidden, level and collapsed.

        Returns:
            0:  Success.
            -1: Row number is out of worksheet bounds.

        """
        if height is not None:
            height = self._pixels_to_height(height)

        return self.set_row(row, height, cell_format, options)

    def set_default_row(self, height=None, hide_unused_rows=False):
        """
        Set the default row properties.

        Args:
            height:           Default height. Optional, defaults to 15.
            hide_unused_rows: Hide unused rows. Optional, defaults to False.

        Returns:
            Nothing.

        """
        if height is None:
            height = self.default_row_height

        if height != self.original_row_height:
            # Store the row change to allow optimizations.
            self.row_size_changed = True
            self.default_row_height = height

        if hide_unused_rows:
            self.default_row_zeroed = 1

    @convert_range_args
    def merge_range(
        self, first_row, first_col, last_row, last_col, data, cell_format=None
    ):
        """
        Merge a range of cells.

        Args:
            first_row:    The first row of the cell range. (zero indexed).
            first_col:    The first column of the cell range.
            last_row:     The last row of the cell range. (zero indexed).
            last_col:     The last column of the cell range.
            data:         Cell data.
            cell_format:  Cell Format object.

        Returns:
             0:    Success.
            -1:    Row or column is out of worksheet bounds.
            other: Return value of write().

        """
        # Merge a range of cells. The first cell should contain the data and
        # the others should be blank. All cells should have the same format.

        # Excel doesn't allow a single cell to be merged
        if first_row == last_row and first_col == last_col:
            warn("Can't merge single cell")
            return

        # Swap last row/col with first row/col as necessary
        if first_row > last_row:
            (first_row, last_row) = (last_row, first_row)
        if first_col > last_col:
            (first_col, last_col) = (last_col, first_col)

        # Check that row and col are valid and store max and min values.
        if self._check_dimensions(first_row, first_col):
            return -1
        if self._check_dimensions(last_row, last_col):
            return -1

        # Check if the merge range overlaps a previous merged or table range.
        # This is a critical file corruption error in Excel.
        cell_range = xl_range(first_row, first_col, last_row, last_col)
        for row in range(first_row, last_row + 1):
            for col in range(first_col, last_col + 1):
                if self.merged_cells.get((row, col)):
                    previous_range = self.merged_cells.get((row, col))
                    raise OverlappingRange(
                        "Merge range '%s' overlaps previous merge range '%s'."
                        % (cell_range, previous_range)
                    )
                elif self.table_cells.get((row, col)):
                    previous_range = self.table_cells.get((row, col))
                    raise OverlappingRange(
                        "Merge range '%s' overlaps previous table range '%s'."
                        % (cell_range, previous_range)
                    )
                else:
                    self.merged_cells[(row, col)] = cell_range

        # Store the merge range.
        self.merge.append([first_row, first_col, last_row, last_col])

        # Write the first cell
        self._write(first_row, first_col, data, cell_format)

        # Pad out the rest of the area with formatted blank cells.
        for row in range(first_row, last_row + 1):
            for col in range(first_col, last_col + 1):
                if row == first_row and col == first_col:
                    continue
                self._write_blank(row, col, "", cell_format)

        return 0

    @convert_range_args
    def autofilter(self, first_row, first_col, last_row, last_col):
        """
        Set the autofilter area in the worksheet.

        Args:
            first_row:    The first row of the cell range. (zero indexed).
            first_col:    The first column of the cell range.
            last_row:     The last row of the cell range. (zero indexed).
            last_col:     The last column of the cell range.

        Returns:
             Nothing.

        """
        # Reverse max and min values if necessary.
        if last_row < first_row:
            (first_row, last_row) = (last_row, first_row)
        if last_col < first_col:
            (first_col, last_col) = (last_col, first_col)

        # Build up the print area range "Sheet1!$A$1:$C$13".
        area = self._convert_name_area(first_row, first_col, last_row, last_col)
        ref = xl_range(first_row, first_col, last_row, last_col)

        self.autofilter_area = area
        self.autofilter_ref = ref
        self.filter_range = [first_col, last_col]

        # Store the filter cell positions for use in the autofit calculation.
        for col in range(first_col, last_col + 1):
            self.filter_cells[(first_row, col)] = True

    def filter_column(self, col, criteria):
        """
        Set the column filter criteria.

        Args:
            col:       Filter column (zero-indexed).
            criteria:  Filter criteria.

        Returns:
             Nothing.

        """
        if not self.autofilter_area:
            warn("Must call autofilter() before filter_column()")
            return

        # Check for a column reference in A1 notation and substitute.
        try:
            int(col)
        except ValueError:
            # Convert col ref to a cell ref and then to a col number.
            col_letter = col
            (_, col) = xl_cell_to_rowcol(col + "1")

            if col >= self.xls_colmax:
                warn("Invalid column '%s'" % col_letter)
                return

        (col_first, col_last) = self.filter_range

        # Reject column if it is outside filter range.
        if col < col_first or col > col_last:
            warn(
                "Column '%d' outside autofilter() column range (%d, %d)"
                % (col, col_first, col_last)
            )
            return

        tokens = self._extract_filter_tokens(criteria)

        if len(tokens) not in (3, 7):
            warn("Incorrect number of tokens in criteria '%s'" % criteria)

        tokens = self._parse_filter_expression(criteria, tokens)

        # Excel handles single or double custom filters as default filters.
        #  We need to check for them and handle them accordingly.
        if len(tokens) == 2 and tokens[0] == 2:
            # Single equality.
            self.filter_column_list(col, [tokens[1]])
        elif len(tokens) == 5 and tokens[0] == 2 and tokens[2] == 1 and tokens[3] == 2:
            # Double equality with "or" operator.
            self.filter_column_list(col, [tokens[1], tokens[4]])
        else:
            # Non default custom filter.
            self.filter_cols[col] = tokens
            self.filter_type[col] = 0

        self.filter_on = 1

    def filter_column_list(self, col, filters):
        """
        Set the column filter criteria in Excel 2007 list style.

        Args:
            col:      Filter column (zero-indexed).
            filters:  List of filter criteria to match.

        Returns:
             Nothing.

        """
        if not self.autofilter_area:
            warn("Must call autofilter() before filter_column()")
            return

        # Check for a column reference in A1 notation and substitute.
        try:
            int(col)
        except ValueError:
            # Convert col ref to a cell ref and then to a col number.
            col_letter = col
            (_, col) = xl_cell_to_rowcol(col + "1")

            if col >= self.xls_colmax:
                warn("Invalid column '%s'" % col_letter)
                return

        (col_first, col_last) = self.filter_range

        # Reject column if it is outside filter range.
        if col < col_first or col > col_last:
            warn(
                "Column '%d' outside autofilter() column range "
                "(%d,%d)" % (col, col_first, col_last)
            )
            return

        self.filter_cols[col] = filters
        self.filter_type[col] = 1
        self.filter_on = 1

    @convert_range_args
    def data_validation(self, first_row, first_col, last_row, last_col, options=None):
        """
        Add a data validation to a worksheet.

        Args:
            first_row:    The first row of the cell range. (zero indexed).
            first_col:    The first column of the cell range.
            last_row:     The last row of the cell range. (zero indexed).
            last_col:     The last column of the cell range.
            options:      Data validation options.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.
            -2: Incorrect parameter or option.
        """
        # Check that row and col are valid without storing the values.
        if self._check_dimensions(first_row, first_col, True, True):
            return -1
        if self._check_dimensions(last_row, last_col, True, True):
            return -1

        if options is None:
            options = {}
        else:
            # Copy the user defined options so they aren't modified.
            options = options.copy()

        # Valid input parameters.
        valid_parameters = {
            "validate",
            "criteria",
            "value",
            "source",
            "minimum",
            "maximum",
            "ignore_blank",
            "dropdown",
            "show_input",
            "input_title",
            "input_message",
            "show_error",
            "error_title",
            "error_message",
            "error_type",
            "other_cells",
            "multi_range",
        }

        # Check for valid input parameters.
        for param_key in options.keys():
            if param_key not in valid_parameters:
                warn("Unknown parameter '%s' in data_validation()" % param_key)
                return -2

        # Map alternative parameter names 'source' or 'minimum' to 'value'.
        if "source" in options:
            options["value"] = options["source"]
        if "minimum" in options:
            options["value"] = options["minimum"]

        # 'validate' is a required parameter.
        if "validate" not in options:
            warn("Parameter 'validate' is required in data_validation()")
            return -2

        # List of  valid validation types.
        valid_types = {
            "any": "none",
            "any value": "none",
            "whole number": "whole",
            "whole": "whole",
            "integer": "whole",
            "decimal": "decimal",
            "list": "list",
            "date": "date",
            "time": "time",
            "text length": "textLength",
            "length": "textLength",
            "custom": "custom",
        }

        # Check for valid validation types.
        if options["validate"] not in valid_types:
            warn(
                "Unknown validation type '%s' for parameter "
                "'validate' in data_validation()" % options["validate"]
            )
            return -2
        else:
            options["validate"] = valid_types[options["validate"]]

        # No action is required for validation type 'any' if there are no
        # input messages to display.
        if (
            options["validate"] == "none"
            and options.get("input_title") is None
            and options.get("input_message") is None
        ):
            return -2

        # The any, list and custom validations don't have a criteria so we use
        # a default of 'between'.
        if (
            options["validate"] == "none"
            or options["validate"] == "list"
            or options["validate"] == "custom"
        ):
            options["criteria"] = "between"
            options["maximum"] = None

        # 'criteria' is a required parameter.
        if "criteria" not in options:
            warn("Parameter 'criteria' is required in data_validation()")
            return -2

        # Valid criteria types.
        criteria_types = {
            "between": "between",
            "not between": "notBetween",
            "equal to": "equal",
            "=": "equal",
            "==": "equal",
            "not equal to": "notEqual",
            "!=": "notEqual",
            "<>": "notEqual",
            "greater than": "greaterThan",
            ">": "greaterThan",
            "less than": "lessThan",
            "<": "lessThan",
            "greater than or equal to": "greaterThanOrEqual",
            ">=": "greaterThanOrEqual",
            "less than or equal to": "lessThanOrEqual",
            "<=": "lessThanOrEqual",
        }

        # Check for valid criteria types.
        if options["criteria"] not in criteria_types:
            warn(
                "Unknown criteria type '%s' for parameter "
                "'criteria' in data_validation()" % options["criteria"]
            )
            return -2
        else:
            options["criteria"] = criteria_types[options["criteria"]]

        # 'Between' and 'Not between' criteria require 2 values.
        if options["criteria"] == "between" or options["criteria"] == "notBetween":
            if "maximum" not in options:
                warn(
                    "Parameter 'maximum' is required in data_validation() "
                    "when using 'between' or 'not between' criteria"
                )
                return -2
        else:
            options["maximum"] = None

        # Valid error dialog types.
        error_types = {
            "stop": 0,
            "warning": 1,
            "information": 2,
        }

        # Check for valid error dialog types.
        if "error_type" not in options:
            options["error_type"] = 0
        elif options["error_type"] not in error_types:
            warn(
                "Unknown criteria type '%s' for parameter 'error_type' "
                "in data_validation()" % options["error_type"]
            )
            return -2
        else:
            options["error_type"] = error_types[options["error_type"]]

        # Convert date/times value if required.
        if (
            options["validate"] in ("date", "time")
            and options["value"]
            and supported_datetime(options["value"])
        ):
            date_time = self._convert_date_time(options["value"])
            # Format date number to the same precision as Excel.
            options["value"] = "%.16g" % date_time

            if options["maximum"] and supported_datetime(options["maximum"]):
                date_time = self._convert_date_time(options["maximum"])
                options["maximum"] = "%.16g" % date_time

        # Check that the input title doesn't exceed the maximum length.
        if options.get("input_title") and len(options["input_title"]) > 32:
            warn(
                "Length of input title '%s' exceeds Excel's limit of 32"
                % options["input_title"]
            )
            return -2

        # Check that the error title doesn't exceed the maximum length.
        if options.get("error_title") and len(options["error_title"]) > 32:
            warn(
                "Length of error title '%s' exceeds Excel's limit of 32"
                % options["error_title"]
            )
            return -2

        # Check that the input message doesn't exceed the maximum length.
        if options.get("input_message") and len(options["input_message"]) > 255:
            warn(
                "Length of input message '%s' exceeds Excel's limit of 255"
                % options["input_message"]
            )
            return -2

        # Check that the error message doesn't exceed the maximum length.
        if options.get("error_message") and len(options["error_message"]) > 255:
            warn(
                "Length of error message '%s' exceeds Excel's limit of 255"
                % options["error_message"]
            )
            return -2

        # Check that the input list doesn't exceed the maximum length.
        if options["validate"] == "list" and isinstance(options["value"], list):
            formula = self._csv_join(*options["value"])
            if len(formula) > 255:
                warn(
                    "Length of list items '%s' exceeds Excel's limit of "
                    "255, use a formula range instead" % formula
                )
                return -2

        # Set some defaults if they haven't been defined by the user.
        if "ignore_blank" not in options:
            options["ignore_blank"] = 1
        if "dropdown" not in options:
            options["dropdown"] = 1
        if "show_input" not in options:
            options["show_input"] = 1
        if "show_error" not in options:
            options["show_error"] = 1

        # These are the cells to which the validation is applied.
        options["cells"] = [[first_row, first_col, last_row, last_col]]

        # A (for now) undocumented parameter to pass additional cell ranges.
        if "other_cells" in options:
            options["cells"].extend(options["other_cells"])

        # Override with user defined multiple range if provided.
        if "multi_range" in options:
            options["multi_range"] = options["multi_range"].replace("$", "")

        # Store the validation information until we close the worksheet.
        self.validations.append(options)

        return 0

    @convert_range_args
    def conditional_format(
        self, first_row, first_col, last_row, last_col, options=None
    ):
        """
        Add a conditional format to a worksheet.

        Args:
            first_row:    The first row of the cell range. (zero indexed).
            first_col:    The first column of the cell range.
            last_row:     The last row of the cell range. (zero indexed).
            last_col:     The last column of the cell range.
            options:      Conditional format options.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.
            -2: Incorrect parameter or option.
        """
        # Check that row and col are valid without storing the values.
        if self._check_dimensions(first_row, first_col, True, True):
            return -1
        if self._check_dimensions(last_row, last_col, True, True):
            return -1

        if options is None:
            options = {}
        else:
            # Copy the user defined options so they aren't modified.
            options = options.copy()

        # Valid input parameters.
        valid_parameter = {
            "type",
            "format",
            "criteria",
            "value",
            "minimum",
            "maximum",
            "stop_if_true",
            "min_type",
            "mid_type",
            "max_type",
            "min_value",
            "mid_value",
            "max_value",
            "min_color",
            "mid_color",
            "max_color",
            "min_length",
            "max_length",
            "multi_range",
            "bar_color",
            "bar_negative_color",
            "bar_negative_color_same",
            "bar_solid",
            "bar_border_color",
            "bar_negative_border_color",
            "bar_negative_border_color_same",
            "bar_no_border",
            "bar_direction",
            "bar_axis_position",
            "bar_axis_color",
            "bar_only",
            "data_bar_2010",
            "icon_style",
            "reverse_icons",
            "icons_only",
            "icons",
        }

        # Check for valid input parameters.
        for param_key in options.keys():
            if param_key not in valid_parameter:
                warn("Unknown parameter '%s' in conditional_format()" % param_key)
                return -2

        # 'type' is a required parameter.
        if "type" not in options:
            warn("Parameter 'type' is required in conditional_format()")
            return -2

        # Valid types.
        valid_type = {
            "cell": "cellIs",
            "date": "date",
            "time": "time",
            "average": "aboveAverage",
            "duplicate": "duplicateValues",
            "unique": "uniqueValues",
            "top": "top10",
            "bottom": "top10",
            "text": "text",
            "time_period": "timePeriod",
            "blanks": "containsBlanks",
            "no_blanks": "notContainsBlanks",
            "errors": "containsErrors",
            "no_errors": "notContainsErrors",
            "2_color_scale": "2_color_scale",
            "3_color_scale": "3_color_scale",
            "data_bar": "dataBar",
            "formula": "expression",
            "icon_set": "iconSet",
        }

        # Check for valid types.
        if options["type"] not in valid_type:
            warn(
                "Unknown value '%s' for parameter 'type' "
                "in conditional_format()" % options["type"]
            )
            return -2
        else:
            if options["type"] == "bottom":
                options["direction"] = "bottom"
            options["type"] = valid_type[options["type"]]

        # Valid criteria types.
        criteria_type = {
            "between": "between",
            "not between": "notBetween",
            "equal to": "equal",
            "=": "equal",
            "==": "equal",
            "not equal to": "notEqual",
            "!=": "notEqual",
            "<>": "notEqual",
            "greater than": "greaterThan",
            ">": "greaterThan",
            "less than": "lessThan",
            "<": "lessThan",
            "greater than or equal to": "greaterThanOrEqual",
            ">=": "greaterThanOrEqual",
            "less than or equal to": "lessThanOrEqual",
            "<=": "lessThanOrEqual",
            "containing": "containsText",
            "not containing": "notContains",
            "begins with": "beginsWith",
            "ends with": "endsWith",
            "yesterday": "yesterday",
            "today": "today",
            "last 7 days": "last7Days",
            "last week": "lastWeek",
            "this week": "thisWeek",
            "next week": "nextWeek",
            "last month": "lastMonth",
            "this month": "thisMonth",
            "next month": "nextMonth",
            # For legacy, but incorrect, support.
            "continue week": "nextWeek",
            "continue month": "nextMonth",
        }

        # Check for valid criteria types.
        if "criteria" in options and options["criteria"] in criteria_type:
            options["criteria"] = criteria_type[options["criteria"]]

        # Convert date/times value if required.
        if options["type"] in ("date", "time"):
            options["type"] = "cellIs"

            if "value" in options:
                if not supported_datetime(options["value"]):
                    warn("Conditional format 'value' must be a datetime object.")
                    return -2
                else:
                    date_time = self._convert_date_time(options["value"])
                    # Format date number to the same precision as Excel.
                    options["value"] = "%.16g" % date_time

            if "minimum" in options:
                if not supported_datetime(options["minimum"]):
                    warn("Conditional format 'minimum' must be a datetime object.")
                    return -2
                else:
                    date_time = self._convert_date_time(options["minimum"])
                    options["minimum"] = "%.16g" % date_time

            if "maximum" in options:
                if not supported_datetime(options["maximum"]):
                    warn("Conditional format 'maximum' must be a datetime object.")
                    return -2
                else:
                    date_time = self._convert_date_time(options["maximum"])
                    options["maximum"] = "%.16g" % date_time

        # Valid icon styles.
        valid_icons = {
            "3_arrows": "3Arrows",  # 1
            "3_flags": "3Flags",  # 2
            "3_traffic_lights_rimmed": "3TrafficLights2",  # 3
            "3_symbols_circled": "3Symbols",  # 4
            "4_arrows": "4Arrows",  # 5
            "4_red_to_black": "4RedToBlack",  # 6
            "4_traffic_lights": "4TrafficLights",  # 7
            "5_arrows_gray": "5ArrowsGray",  # 8
            "5_quarters": "5Quarters",  # 9
            "3_arrows_gray": "3ArrowsGray",  # 10
            "3_traffic_lights": "3TrafficLights",  # 11
            "3_signs": "3Signs",  # 12
            "3_symbols": "3Symbols2",  # 13
            "4_arrows_gray": "4ArrowsGray",  # 14
            "4_ratings": "4Rating",  # 15
            "5_arrows": "5Arrows",  # 16
            "5_ratings": "5Rating",
        }  # 17

        # Set the icon set properties.
        if options["type"] == "iconSet":
            # An icon_set must have an icon style.
            if not options.get("icon_style"):
                warn(
                    "The 'icon_style' parameter must be specified when "
                    "'type' == 'icon_set' in conditional_format()"
                )
                return -3

            # Check for valid icon styles.
            if options["icon_style"] not in valid_icons:
                warn(
                    "Unknown icon_style '%s' in conditional_format()"
                    % options["icon_style"]
                )
                return -2
            else:
                options["icon_style"] = valid_icons[options["icon_style"]]

            # Set the number of icons for the icon style.
            options["total_icons"] = 3
            if options["icon_style"].startswith("4"):
                options["total_icons"] = 4
            elif options["icon_style"].startswith("5"):
                options["total_icons"] = 5

            options["icons"] = self._set_icon_props(
                options.get("total_icons"), options.get("icons")
            )

        # Swap last row/col for first row/col as necessary
        if first_row > last_row:
            first_row, last_row = last_row, first_row

        if first_col > last_col:
            first_col, last_col = last_col, first_col

        # Set the formatting range.
        cell_range = xl_range(first_row, first_col, last_row, last_col)
        start_cell = xl_rowcol_to_cell(first_row, first_col)

        # Override with user defined multiple range if provided.
        if "multi_range" in options:
            cell_range = options["multi_range"]
            cell_range = cell_range.replace("$", "")

        # Get the dxf format index.
        if "format" in options and options["format"]:
            options["format"] = options["format"]._get_dxf_index()

        # Set the priority based on the order of adding.
        options["priority"] = self.dxf_priority
        self.dxf_priority += 1

        # Check for 2010 style data_bar parameters.
        if (
            self.use_data_bars_2010
            or options.get("data_bar_2010")
            or options.get("bar_solid")
            or options.get("bar_border_color")
            or options.get("bar_negative_color")
            or options.get("bar_negative_color_same")
            or options.get("bar_negative_border_color")
            or options.get("bar_negative_border_color_same")
            or options.get("bar_no_border")
            or options.get("bar_axis_position")
            or options.get("bar_axis_color")
            or options.get("bar_direction")
        ):
            options["is_data_bar_2010"] = True

        # Special handling of text criteria.
        if options["type"] == "text":
            if options["criteria"] == "containsText":
                options["type"] = "containsText"
                options["formula"] = 'NOT(ISERROR(SEARCH("%s",%s)))' % (
                    options["value"],
                    start_cell,
                )
            elif options["criteria"] == "notContains":
                options["type"] = "notContainsText"
                options["formula"] = 'ISERROR(SEARCH("%s",%s))' % (
                    options["value"],
                    start_cell,
                )
            elif options["criteria"] == "beginsWith":
                options["type"] = "beginsWith"
                options["formula"] = 'LEFT(%s,%d)="%s"' % (
                    start_cell,
                    len(options["value"]),
                    options["value"],
                )
            elif options["criteria"] == "endsWith":
                options["type"] = "endsWith"
                options["formula"] = 'RIGHT(%s,%d)="%s"' % (
                    start_cell,
                    len(options["value"]),
                    options["value"],
                )
            else:
                warn(
                    "Invalid text criteria '%s' "
                    "in conditional_format()" % options["criteria"]
                )

        # Special handling of time time_period criteria.
        if options["type"] == "timePeriod":
            if options["criteria"] == "yesterday":
                options["formula"] = "FLOOR(%s,1)=TODAY()-1" % start_cell

            elif options["criteria"] == "today":
                options["formula"] = "FLOOR(%s,1)=TODAY()" % start_cell

            elif options["criteria"] == "tomorrow":
                options["formula"] = "FLOOR(%s,1)=TODAY()+1" % start_cell

            elif options["criteria"] == "last7Days":
                options[
                    "formula"
                ] = "AND(TODAY()-FLOOR(%s,1)<=6,FLOOR(%s,1)<=TODAY())" % (
                    start_cell,
                    start_cell,
                )

            elif options["criteria"] == "lastWeek":
                options["formula"] = (
                    "AND(TODAY()-ROUNDDOWN(%s,0)>=(WEEKDAY(TODAY())),"
                    "TODAY()-ROUNDDOWN(%s,0)<(WEEKDAY(TODAY())+7))"
                    % (start_cell, start_cell)
                )

            elif options["criteria"] == "thisWeek":
                options["formula"] = (
                    "AND(TODAY()-ROUNDDOWN(%s,0)<=WEEKDAY(TODAY())-1,"
                    "ROUNDDOWN(%s,0)-TODAY()<=7-WEEKDAY(TODAY()))"
                    % (start_cell, start_cell)
                )

            elif options["criteria"] == "nextWeek":
                options["formula"] = (
                    "AND(ROUNDDOWN(%s,0)-TODAY()>(7-WEEKDAY(TODAY())),"
                    "ROUNDDOWN(%s,0)-TODAY()<(15-WEEKDAY(TODAY())))"
                    % (start_cell, start_cell)
                )

            elif options["criteria"] == "lastMonth":
                options["formula"] = (
                    "AND(MONTH(%s)=MONTH(TODAY())-1,OR(YEAR(%s)=YEAR("
                    "TODAY()),AND(MONTH(%s)=1,YEAR(A1)=YEAR(TODAY())-1)))"
                    % (start_cell, start_cell, start_cell)
                )

            elif options["criteria"] == "thisMonth":
                options[
                    "formula"
                ] = "AND(MONTH(%s)=MONTH(TODAY()),YEAR(%s)=YEAR(TODAY()))" % (
                    start_cell,
                    start_cell,
                )

            elif options["criteria"] == "nextMonth":
                options["formula"] = (
                    "AND(MONTH(%s)=MONTH(TODAY())+1,OR(YEAR(%s)=YEAR("
                    "TODAY()),AND(MONTH(%s)=12,YEAR(%s)=YEAR(TODAY())+1)))"
                    % (start_cell, start_cell, start_cell, start_cell)
                )

            else:
                warn(
                    "Invalid time_period criteria '%s' "
                    "in conditional_format()" % options["criteria"]
                )

        # Special handling of blanks/error types.
        if options["type"] == "containsBlanks":
            options["formula"] = "LEN(TRIM(%s))=0" % start_cell

        if options["type"] == "notContainsBlanks":
            options["formula"] = "LEN(TRIM(%s))>0" % start_cell

        if options["type"] == "containsErrors":
            options["formula"] = "ISERROR(%s)" % start_cell

        if options["type"] == "notContainsErrors":
            options["formula"] = "NOT(ISERROR(%s))" % start_cell

        # Special handling for 2 color scale.
        if options["type"] == "2_color_scale":
            options["type"] = "colorScale"

            # Color scales don't use any additional formatting.
            options["format"] = None

            # Turn off 3 color parameters.
            options["mid_type"] = None
            options["mid_color"] = None

            options.setdefault("min_type", "min")
            options.setdefault("max_type", "max")
            options.setdefault("min_value", 0)
            options.setdefault("max_value", 0)
            options.setdefault("min_color", "#FF7128")
            options.setdefault("max_color", "#FFEF9C")

            options["min_color"] = xl_color(options["min_color"])
            options["max_color"] = xl_color(options["max_color"])

        # Special handling for 3 color scale.
        if options["type"] == "3_color_scale":
            options["type"] = "colorScale"

            # Color scales don't use any additional formatting.
            options["format"] = None

            options.setdefault("min_type", "min")
            options.setdefault("mid_type", "percentile")
            options.setdefault("max_type", "max")
            options.setdefault("min_value", 0)
            options.setdefault("max_value", 0)
            options.setdefault("min_color", "#F8696B")
            options.setdefault("mid_color", "#FFEB84")
            options.setdefault("max_color", "#63BE7B")

            options["min_color"] = xl_color(options["min_color"])
            options["mid_color"] = xl_color(options["mid_color"])
            options["max_color"] = xl_color(options["max_color"])

            # Set a default mid value.
            if "mid_value" not in options:
                options["mid_value"] = 50

        # Special handling for data bar.
        if options["type"] == "dataBar":
            # Color scales don't use any additional formatting.
            options["format"] = None

            if not options.get("min_type"):
                options["min_type"] = "min"
                options["x14_min_type"] = "autoMin"
            else:
                options["x14_min_type"] = options["min_type"]

            if not options.get("max_type"):
                options["max_type"] = "max"
                options["x14_max_type"] = "autoMax"
            else:
                options["x14_max_type"] = options["max_type"]

            options.setdefault("min_value", 0)
            options.setdefault("max_value", 0)
            options.setdefault("bar_color", "#638EC6")
            options.setdefault("bar_border_color", options["bar_color"])
            options.setdefault("bar_only", False)
            options.setdefault("bar_no_border", False)
            options.setdefault("bar_solid", False)
            options.setdefault("bar_direction", "")
            options.setdefault("bar_negative_color", "#FF0000")
            options.setdefault("bar_negative_border_color", "#FF0000")
            options.setdefault("bar_negative_color_same", False)
            options.setdefault("bar_negative_border_color_same", False)
            options.setdefault("bar_axis_position", "")
            options.setdefault("bar_axis_color", "#000000")

            options["bar_color"] = xl_color(options["bar_color"])
            options["bar_border_color"] = xl_color(options["bar_border_color"])
            options["bar_axis_color"] = xl_color(options["bar_axis_color"])
            options["bar_negative_color"] = xl_color(options["bar_negative_color"])
            options["bar_negative_border_color"] = xl_color(
                options["bar_negative_border_color"]
            )

        # Adjust for 2010 style data_bar parameters.
        if options.get("is_data_bar_2010"):
            self.excel_version = 2010

            if options["min_type"] == "min" and options["min_value"] == 0:
                options["min_value"] = None

            if options["max_type"] == "max" and options["max_value"] == 0:
                options["max_value"] = None

            options["range"] = cell_range

        # Strip the leading = from formulas.
        try:
            options["min_value"] = options["min_value"].lstrip("=")
        except (KeyError, AttributeError):
            pass
        try:
            options["mid_value"] = options["mid_value"].lstrip("=")
        except (KeyError, AttributeError):
            pass
        try:
            options["max_value"] = options["max_value"].lstrip("=")
        except (KeyError, AttributeError):
            pass

        # Store the conditional format until we close the worksheet.
        if cell_range in self.cond_formats:
            self.cond_formats[cell_range].append(options)
        else:
            self.cond_formats[cell_range] = [options]

        return 0

    @convert_range_args
    def add_table(self, first_row, first_col, last_row, last_col, options=None):
        """
        Add an Excel table to a worksheet.

        Args:
            first_row:    The first row of the cell range. (zero indexed).
            first_col:    The first column of the cell range.
            last_row:     The last row of the cell range. (zero indexed).
            last_col:     The last column of the cell range.
            options:      Table format options. (Optional)

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.
            -2: Incorrect parameter or option.
            -3: Not supported in constant_memory mode.
        """
        table = {}
        col_formats = {}

        if options is None:
            options = {}
        else:
            # Copy the user defined options so they aren't modified.
            options = options.copy()

        if self.constant_memory:
            warn("add_table() isn't supported in 'constant_memory' mode")
            return -3

        # Check that row and col are valid without storing the values.
        if self._check_dimensions(first_row, first_col, True, True):
            return -1
        if self._check_dimensions(last_row, last_col, True, True):
            return -1

        # Swap last row/col for first row/col as necessary.
        if first_row > last_row:
            (first_row, last_row) = (last_row, first_row)
        if first_col > last_col:
            (first_col, last_col) = (last_col, first_col)

        # Check if the table range overlaps a previous merged or table range.
        # This is a critical file corruption error in Excel.
        cell_range = xl_range(first_row, first_col, last_row, last_col)
        for row in range(first_row, last_row + 1):
            for col in range(first_col, last_col + 1):
                if self.table_cells.get((row, col)):
                    previous_range = self.table_cells.get((row, col))
                    raise OverlappingRange(
                        "Table range '%s' overlaps previous table range '%s'."
                        % (cell_range, previous_range)
                    )
                elif self.merged_cells.get((row, col)):
                    previous_range = self.merged_cells.get((row, col))
                    raise OverlappingRange(
                        "Table range '%s' overlaps previous merge range '%s'."
                        % (cell_range, previous_range)
                    )
                else:
                    self.table_cells[(row, col)] = cell_range

        # Valid input parameters.
        valid_parameter = {
            "autofilter",
            "banded_columns",
            "banded_rows",
            "columns",
            "data",
            "first_column",
            "header_row",
            "last_column",
            "name",
            "style",
            "total_row",
        }

        # Check for valid input parameters.
        for param_key in options.keys():
            if param_key not in valid_parameter:
                warn("Unknown parameter '%s' in add_table()" % param_key)
                return -2

        # Turn on Excel's defaults.
        options["banded_rows"] = options.get("banded_rows", True)
        options["header_row"] = options.get("header_row", True)
        options["autofilter"] = options.get("autofilter", True)

        # Check that there are enough rows.
        num_rows = last_row - first_row
        if options["header_row"]:
            num_rows -= 1

        if num_rows < 0:
            warn("Must have at least one data row in in add_table()")
            return -2

        # Set the table options.
        table["show_first_col"] = options.get("first_column", False)
        table["show_last_col"] = options.get("last_column", False)
        table["show_row_stripes"] = options.get("banded_rows", False)
        table["show_col_stripes"] = options.get("banded_columns", False)
        table["header_row_count"] = options.get("header_row", 0)
        table["totals_row_shown"] = options.get("total_row", False)

        # Set the table name.
        if "name" in options:
            name = options["name"]
            table["name"] = name

            if " " in name:
                warn("Name '%s' in add_table() cannot contain spaces" % name)
                return -2

            # Warn if the name contains invalid chars as defined by Excel.
            if not re.match(r"^[\w\\][\w\\.]*$", name, re.UNICODE) or re.match(
                r"^\d", name
            ):
                warn("Invalid Excel characters in add_table(): '%s'" % name)
                return -2

            # Warn if the name looks like a cell name.
            if re.match(r"^[a-zA-Z][a-zA-Z]?[a-dA-D]?\d+$", name):
                warn("Name looks like a cell name in add_table(): '%s'" % name)
                return -2

            # Warn if the name looks like a R1C1 cell reference.
            if re.match(r"^[rcRC]$", name) or re.match(r"^[rcRC]\d+[rcRC]\d+$", name):
                warn("Invalid name '%s' like a RC cell ref in add_table()" % name)
                return -2

        # Set the table style.
        if "style" in options:
            table["style"] = options["style"]

            if table["style"] is None:
                table["style"] = ""

            # Remove whitespace from style name.
            table["style"] = table["style"].replace(" ", "")
        else:
            table["style"] = "TableStyleMedium9"

        # Set the data range rows (without the header and footer).
        first_data_row = first_row
        last_data_row = last_row

        if options.get("header_row"):
            first_data_row += 1

        if options.get("total_row"):
            last_data_row -= 1

        # Set the table and autofilter ranges.
        table["range"] = xl_range(first_row, first_col, last_row, last_col)

        table["a_range"] = xl_range(first_row, first_col, last_data_row, last_col)

        # If the header row if off the default is to turn autofilter off.
        if not options["header_row"]:
            options["autofilter"] = 0

        # Set the autofilter range.
        if options["autofilter"]:
            table["autofilter"] = table["a_range"]

        # Add the table columns.
        col_id = 1
        table["columns"] = []
        seen_names = {}

        for col_num in range(first_col, last_col + 1):
            # Set up the default column data.
            col_data = {
                "id": col_id,
                "name": "Column" + str(col_id),
                "total_string": "",
                "total_function": "",
                "custom_total": "",
                "total_value": 0,
                "formula": "",
                "format": None,
                "name_format": None,
            }

            # Overwrite the defaults with any user defined values.
            if "columns" in options:
                # Check if there are user defined values for this column.
                if col_id <= len(options["columns"]):
                    user_data = options["columns"][col_id - 1]
                else:
                    user_data = None

                if user_data:
                    # Get the column format.
                    xformat = user_data.get("format", None)

                    # Map user defined values to internal values.
                    if user_data.get("header"):
                        col_data["name"] = user_data["header"]

                    # Excel requires unique case insensitive header names.
                    header_name = col_data["name"]
                    name = header_name.lower()
                    if name in seen_names:
                        warn("Duplicate header name in add_table(): '%s'" % name)
                        return -2
                    else:
                        seen_names[name] = True

                    col_data["name_format"] = user_data.get("header_format")

                    # Handle the column formula.
                    if "formula" in user_data and user_data["formula"]:
                        formula = user_data["formula"]

                        # Remove the formula '=' sign if it exists.
                        if formula.startswith("="):
                            formula = formula.lstrip("=")

                        # Convert Excel 2010 "@" ref to 2007 "#This Row".
                        formula = formula.replace("@", "[#This Row],")

                        # Escape any future functions.
                        formula = self._prepare_formula(formula, True)

                        col_data["formula"] = formula
                        # We write the formulas below after the table data.

                    # Handle the function for the total row.
                    if user_data.get("total_function"):
                        function = user_data["total_function"]
                        if function == "count_nums":
                            function = "countNums"
                        if function == "std_dev":
                            function = "stdDev"

                        subtotals = set(
                            [
                                "average",
                                "countNums",
                                "count",
                                "max",
                                "min",
                                "stdDev",
                                "sum",
                                "var",
                            ]
                        )

                        if function in subtotals:
                            formula = self._table_function_to_formula(
                                function, col_data["name"]
                            )
                        else:
                            formula = self._prepare_formula(function, True)
                            col_data["custom_total"] = formula
                            function = "custom"

                        col_data["total_function"] = function

                        value = user_data.get("total_value", 0)

                        self._write_formula(last_row, col_num, formula, xformat, value)

                    elif user_data.get("total_string"):
                        # Total label only (not a function).
                        total_string = user_data["total_string"]
                        col_data["total_string"] = total_string

                        self._write_string(
                            last_row, col_num, total_string, user_data.get("format")
                        )

                    # Get the dxf format index.
                    if xformat is not None:
                        col_data["format"] = xformat._get_dxf_index()

                    # Store the column format for writing the cell data.
                    # It doesn't matter if it is undefined.
                    col_formats[col_id - 1] = xformat

            # Store the column data.
            table["columns"].append(col_data)

            # Write the column headers to the worksheet.
            if options["header_row"]:
                self._write_string(
                    first_row, col_num, col_data["name"], col_data["name_format"]
                )

            col_id += 1

        # Write the cell data if supplied.
        if "data" in options:
            data = options["data"]

            i = 0  # For indexing the row data.
            for row in range(first_data_row, last_data_row + 1):
                j = 0  # For indexing the col data.
                for col in range(first_col, last_col + 1):
                    if i < len(data) and j < len(data[i]):
                        token = data[i][j]
                        if j in col_formats:
                            self._write(row, col, token, col_formats[j])
                        else:
                            self._write(row, col, token, None)
                    j += 1
                i += 1

        # Write any columns formulas after the user supplied table data to
        # overwrite it if required.
        for col_id, col_num in enumerate(range(first_col, last_col + 1)):
            column_data = table["columns"][col_id]
            if column_data and column_data["formula"]:
                formula_format = col_formats.get(col_id)
                formula = column_data["formula"]

                for row in range(first_data_row, last_data_row + 1):
                    self._write_formula(row, col_num, formula, formula_format)

        # Store the table data.
        self.tables.append(table)

        # Store the filter cell positions for use in the autofit calculation.
        if options["autofilter"]:
            for col in range(first_col, last_col + 1):
                self.filter_cells[(first_row, col)] = True

        return 0

    @convert_cell_args
    def add_sparkline(self, row, col, options=None):
        """
        Add sparklines to the worksheet.

        Args:
            row:     The cell row (zero indexed).
            col:     The cell column (zero indexed).
            options: Sparkline formatting options.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.
            -2: Incorrect parameter or option.

        """

        # Check that row and col are valid without storing the values.
        if self._check_dimensions(row, col, True, True):
            return -1

        sparkline = {"locations": [xl_rowcol_to_cell(row, col)]}

        if options is None:
            options = {}

        # Valid input parameters.
        valid_parameters = {
            "location",
            "range",
            "type",
            "high_point",
            "low_point",
            "negative_points",
            "first_point",
            "last_point",
            "markers",
            "style",
            "series_color",
            "negative_color",
            "markers_color",
            "first_color",
            "last_color",
            "high_color",
            "low_color",
            "max",
            "min",
            "axis",
            "reverse",
            "empty_cells",
            "show_hidden",
            "plot_hidden",
            "date_axis",
            "weight",
        }

        # Check for valid input parameters.
        for param_key in options.keys():
            if param_key not in valid_parameters:
                warn("Unknown parameter '%s' in add_sparkline()" % param_key)
                return -1

        # 'range' is a required parameter.
        if "range" not in options:
            warn("Parameter 'range' is required in add_sparkline()")
            return -2

        # Handle the sparkline type.
        spark_type = options.get("type", "line")

        if spark_type not in ("line", "column", "win_loss"):
            warn(
                "Parameter 'type' must be 'line', 'column' "
                "or 'win_loss' in add_sparkline()"
            )
            return -2

        if spark_type == "win_loss":
            spark_type = "stacked"
        sparkline["type"] = spark_type

        # We handle single location/range values or list of values.
        if "location" in options:
            if isinstance(options["location"], list):
                sparkline["locations"] = options["location"]
            else:
                sparkline["locations"] = [options["location"]]

        if isinstance(options["range"], list):
            sparkline["ranges"] = options["range"]
        else:
            sparkline["ranges"] = [options["range"]]

        range_count = len(sparkline["ranges"])
        location_count = len(sparkline["locations"])

        # The ranges and locations must match.
        if range_count != location_count:
            warn(
                "Must have the same number of location and range "
                "parameters in add_sparkline()"
            )
            return -2

        # Store the count.
        sparkline["count"] = len(sparkline["locations"])

        # Get the worksheet name for the range conversion below.
        sheetname = quote_sheetname(self.name)

        # Cleanup the input ranges.
        new_ranges = []
        for spark_range in sparkline["ranges"]:
            # Remove the absolute reference $ symbols.
            spark_range = spark_range.replace("$", "")

            # Remove the = from formula.
            spark_range = spark_range.lstrip("=")

            # Convert a simple range into a full Sheet1!A1:D1 range.
            if "!" not in spark_range:
                spark_range = sheetname + "!" + spark_range

            new_ranges.append(spark_range)

        sparkline["ranges"] = new_ranges

        # Cleanup the input locations.
        new_locations = []
        for location in sparkline["locations"]:
            location = location.replace("$", "")
            new_locations.append(location)

        sparkline["locations"] = new_locations

        # Map options.
        sparkline["high"] = options.get("high_point")
        sparkline["low"] = options.get("low_point")
        sparkline["negative"] = options.get("negative_points")
        sparkline["first"] = options.get("first_point")
        sparkline["last"] = options.get("last_point")
        sparkline["markers"] = options.get("markers")
        sparkline["min"] = options.get("min")
        sparkline["max"] = options.get("max")
        sparkline["axis"] = options.get("axis")
        sparkline["reverse"] = options.get("reverse")
        sparkline["hidden"] = options.get("show_hidden")
        sparkline["weight"] = options.get("weight")

        # Map empty cells options.
        empty = options.get("empty_cells", "")

        if empty == "zero":
            sparkline["empty"] = 0
        elif empty == "connect":
            sparkline["empty"] = "span"
        else:
            sparkline["empty"] = "gap"

        # Map the date axis range.
        date_range = options.get("date_axis")

        if date_range and "!" not in date_range:
            date_range = sheetname + "!" + date_range

        sparkline["date_axis"] = date_range

        # Set the sparkline styles.
        style_id = options.get("style", 0)
        style = get_sparkline_style(style_id)

        sparkline["series_color"] = style["series"]
        sparkline["negative_color"] = style["negative"]
        sparkline["markers_color"] = style["markers"]
        sparkline["first_color"] = style["first"]
        sparkline["last_color"] = style["last"]
        sparkline["high_color"] = style["high"]
        sparkline["low_color"] = style["low"]

        # Override the style colors with user defined colors.
        self._set_spark_color(sparkline, options, "series_color")
        self._set_spark_color(sparkline, options, "negative_color")
        self._set_spark_color(sparkline, options, "markers_color")
        self._set_spark_color(sparkline, options, "first_color")
        self._set_spark_color(sparkline, options, "last_color")
        self._set_spark_color(sparkline, options, "high_color")
        self._set_spark_color(sparkline, options, "low_color")

        self.sparklines.append(sparkline)

        return 0

    @convert_range_args
    def set_selection(self, first_row, first_col, last_row, last_col):
        """
        Set the selected cell or cells in a worksheet

        Args:
            first_row:    The first row of the cell range. (zero indexed).
            first_col:    The first column of the cell range.
            last_row:     The last row of the cell range. (zero indexed).
            last_col:     The last column of the cell range.

        Returns:
            0:  Nothing.
        """
        pane = None

        # Range selection. Do this before swapping max/min to allow the
        # selection direction to be reversed.
        active_cell = xl_rowcol_to_cell(first_row, first_col)

        # Swap last row/col for first row/col if necessary
        if first_row > last_row:
            (first_row, last_row) = (last_row, first_row)

        if first_col > last_col:
            (first_col, last_col) = (last_col, first_col)

        sqref = xl_range(first_row, first_col, last_row, last_col)

        # Selection isn't set for cell A1.
        if sqref == "A1":
            return

        self.selections = [[pane, active_cell, sqref]]

    @convert_cell_args
    def set_top_left_cell(self, row=0, col=0):
        """
        Set the first visible cell at the top left of a worksheet.

        Args:
            row: The cell row (zero indexed).
            col: The cell column (zero indexed).

        Returns:
            0:  Nothing.
        """

        if row == 0 and col == 0:
            return

        self.top_left_cell = xl_rowcol_to_cell(row, col)

    def outline_settings(
        self, visible=1, symbols_below=1, symbols_right=1, auto_style=0
    ):
        """
        Control outline settings.

        Args:
            visible:       Outlines are visible. Optional, defaults to True.
            symbols_below: Show row outline symbols below the outline bar.
                           Optional, defaults to True.
            symbols_right: Show column outline symbols to the right of the
                           outline bar. Optional, defaults to True.
            auto_style:    Use Automatic style. Optional, defaults to False.

        Returns:
            0:  Nothing.
        """
        self.outline_on = visible
        self.outline_below = symbols_below
        self.outline_right = symbols_right
        self.outline_style = auto_style

        self.outline_changed = True

    @convert_cell_args
    def freeze_panes(self, row, col, top_row=None, left_col=None, pane_type=0):
        """
        Create worksheet panes and mark them as frozen.

        Args:
            row:      The cell row (zero indexed).
            col:      The cell column (zero indexed).
            top_row:  Topmost visible row in scrolling region of pane.
            left_col: Leftmost visible row in scrolling region of pane.

        Returns:
            0:  Nothing.

        """
        if top_row is None:
            top_row = row

        if left_col is None:
            left_col = col

        self.panes = [row, col, top_row, left_col, pane_type]

    @convert_cell_args
    def split_panes(self, x, y, top_row=None, left_col=None):
        """
        Create worksheet panes and mark them as split.

        Args:
            x:        The position for the vertical split.
            y:        The position for the horizontal split.
            top_row:  Topmost visible row in scrolling region of pane.
            left_col: Leftmost visible row in scrolling region of pane.

        Returns:
            0:  Nothing.

        """
        # Same as freeze panes with a different pane type.
        self.freeze_panes(x, y, top_row, left_col, 2)

    def set_zoom(self, zoom=100):
        """
        Set the worksheet zoom factor.

        Args:
            zoom: Scale factor: 10 <= zoom <= 400.

        Returns:
            Nothing.

        """
        # Ensure the zoom scale is in Excel's range.
        if zoom < 10 or zoom > 400:
            warn("Zoom factor %d outside range: 10 <= zoom <= 400" % zoom)
            zoom = 100

        self.zoom = int(zoom)

    def right_to_left(self):
        """
        Display the worksheet right to left for some versions of Excel.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.is_right_to_left = 1

    def hide_zero(self):
        """
        Hide zero values in worksheet cells.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.show_zeros = 0

    def set_tab_color(self, color):
        """
        Set the color of the worksheet tab.

        Args:
            color: A #RGB color index.

        Returns:
            Nothing.

        """
        self.tab_color = xl_color(color)

    def protect(self, password="", options=None):
        """
        Set the password and protection options of the worksheet.

        Args:
            password: An optional password string.
            options:  A dictionary of worksheet objects to protect.

        Returns:
            Nothing.

        """
        if password != "":
            password = self._encode_password(password)

        if not options:
            options = {}

        # Default values for objects that can be protected.
        defaults = {
            "sheet": True,
            "content": False,
            "objects": False,
            "scenarios": False,
            "format_cells": False,
            "format_columns": False,
            "format_rows": False,
            "insert_columns": False,
            "insert_rows": False,
            "insert_hyperlinks": False,
            "delete_columns": False,
            "delete_rows": False,
            "select_locked_cells": True,
            "sort": False,
            "autofilter": False,
            "pivot_tables": False,
            "select_unlocked_cells": True,
        }

        # Overwrite the defaults with user specified values.
        for key in options.keys():
            if key in defaults:
                defaults[key] = options[key]
            else:
                warn("Unknown protection object: '%s'" % key)

        # Set the password after the user defined values.
        defaults["password"] = password

        self.protect_options = defaults

    def unprotect_range(self, cell_range, range_name=None, password=None):
        """
        Unprotect ranges within a protected worksheet.

        Args:
            cell_range: The cell or cell range to unprotect.
            range_name: An optional name for the range.
            password:   An optional password string. (undocumented)

        Returns:
            Nothing.

        """
        if cell_range is None:
            warn("Cell range must be specified in unprotect_range()")
            return -1

        # Sanitize the cell range.
        cell_range = cell_range.lstrip("=")
        cell_range = cell_range.replace("$", "")

        self.num_protected_ranges += 1

        if range_name is None:
            range_name = "Range" + str(self.num_protected_ranges)

        if password:
            password = self._encode_password(password)

        self.protected_ranges.append((cell_range, range_name, password))

    @convert_cell_args
    def insert_button(self, row, col, options=None):
        """
        Insert a button form object into the worksheet.

        Args:
            row:     The cell row (zero indexed).
            col:     The cell column (zero indexed).
            options: Button formatting options.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.

        """
        # Check insert (row, col) without storing.
        if self._check_dimensions(row, col, True, True):
            warn("Cannot insert button at (%d, %d)." % (row, col))
            return -1

        if options is None:
            options = {}

        button = self._button_params(row, col, options)

        self.buttons_list.append(button)

        self.has_vml = 1

        return 0

    ###########################################################################
    #
    # Public API. Page Setup methods.
    #
    ###########################################################################
    def set_landscape(self):
        """
        Set the page orientation as landscape.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.orientation = 0
        self.page_setup_changed = True

    def set_portrait(self):
        """
        Set the page orientation as portrait.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.orientation = 1
        self.page_setup_changed = True

    def set_page_view(self, view=1):
        """
        Set the page view mode.

        Args:
            0: Normal view mode
            1: Page view mode (the default)
            2: Page break view mode

        Returns:
            Nothing.

        """
        self.page_view = view

    def set_pagebreak_view(self, view=1):
        """
        Set the page view mode.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.page_view = 2

    def set_paper(self, paper_size):
        """
        Set the paper type. US Letter = 1, A4 = 9.

        Args:
            paper_size: Paper index.

        Returns:
            Nothing.

        """
        if paper_size:
            self.paper_size = paper_size
            self.page_setup_changed = True

    def center_horizontally(self):
        """
        Center the page horizontally.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.print_options_changed = True
        self.hcenter = 1

    def center_vertically(self):
        """
        Center the page vertically.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.print_options_changed = True
        self.vcenter = 1

    def set_margins(self, left=0.7, right=0.7, top=0.75, bottom=0.75):
        """
        Set all the page margins in inches.

        Args:
            left:   Left margin.
            right:  Right margin.
            top:    Top margin.
            bottom: Bottom margin.

        Returns:
            Nothing.

        """
        self.margin_left = left
        self.margin_right = right
        self.margin_top = top
        self.margin_bottom = bottom

    def set_header(self, header="", options=None, margin=None):
        """
        Set the page header caption and optional margin.

        Args:
            header:  Header string.
            margin:  Header margin.
            options: Header options, mainly for images.

        Returns:
            Nothing.

        """
        header_orig = header
        header = header.replace("&[Picture]", "&G")

        if len(header) > 255:
            warn("Header string cannot be longer than Excel's limit of 255 characters")
            return

        if options is not None:
            # For backward compatibility allow options to be the margin.
            if not isinstance(options, dict):
                options = {"margin": options}
        else:
            options = {}

        # Copy the user defined options so they aren't modified.
        options = options.copy()

        # For backward compatibility.
        if margin is not None:
            options["margin"] = margin

        # Reset the list in case the function is called more than once.
        self.header_images = []

        if options.get("image_left"):
            self.header_images.append(
                [options.get("image_left"), options.get("image_data_left"), "LH"]
            )

        if options.get("image_center"):
            self.header_images.append(
                [options.get("image_center"), options.get("image_data_center"), "CH"]
            )

        if options.get("image_right"):
            self.header_images.append(
                [options.get("image_right"), options.get("image_data_right"), "RH"]
            )

        placeholder_count = header.count("&G")
        image_count = len(self.header_images)

        if placeholder_count != image_count:
            warn(
                "Number of header images (%s) doesn't match placeholder "
                "count (%s) in string: %s"
                % (image_count, placeholder_count, header_orig)
            )
            self.header_images = []
            return

        if "align_with_margins" in options:
            self.header_footer_aligns = options["align_with_margins"]

        if "scale_with_doc" in options:
            self.header_footer_scales = options["scale_with_doc"]

        self.header = header
        self.margin_header = options.get("margin", 0.3)
        self.header_footer_changed = True

        if image_count:
            self.has_header_vml = True

    def set_footer(self, footer="", options=None, margin=None):
        """
        Set the page footer caption and optional margin.

        Args:
            footer:  Footer string.
            margin:  Footer margin.
            options: Footer options, mainly for images.

        Returns:
            Nothing.

        """
        footer_orig = footer
        footer = footer.replace("&[Picture]", "&G")

        if len(footer) > 255:
            warn("Footer string cannot be longer than Excel's limit of 255 characters")
            return

        if options is not None:
            # For backward compatibility allow options to be the margin.
            if not isinstance(options, dict):
                options = {"margin": options}
        else:
            options = {}

        # Copy the user defined options so they aren't modified.
        options = options.copy()

        # For backward compatibility.
        if margin is not None:
            options["margin"] = margin

        # Reset the list in case the function is called more than once.
        self.footer_images = []

        if options.get("image_left"):
            self.footer_images.append(
                [options.get("image_left"), options.get("image_data_left"), "LF"]
            )

        if options.get("image_center"):
            self.footer_images.append(
                [options.get("image_center"), options.get("image_data_center"), "CF"]
            )

        if options.get("image_right"):
            self.footer_images.append(
                [options.get("image_right"), options.get("image_data_right"), "RF"]
            )

        placeholder_count = footer.count("&G")
        image_count = len(self.footer_images)

        if placeholder_count != image_count:
            warn(
                "Number of footer images (%s) doesn't match placeholder "
                "count (%s) in string: %s"
                % (image_count, placeholder_count, footer_orig)
            )
            self.footer_images = []
            return

        if "align_with_margins" in options:
            self.header_footer_aligns = options["align_with_margins"]

        if "scale_with_doc" in options:
            self.header_footer_scales = options["scale_with_doc"]

        self.footer = footer
        self.margin_footer = options.get("margin", 0.3)
        self.header_footer_changed = True

        if image_count:
            self.has_header_vml = True

    def repeat_rows(self, first_row, last_row=None):
        """
        Set the rows to repeat at the top of each printed page.

        Args:
            first_row: Start row for range.
            last_row: End row for range.

        Returns:
            Nothing.

        """
        if last_row is None:
            last_row = first_row

        # Convert rows to 1 based.
        first_row += 1
        last_row += 1

        # Create the row range area like: $1:$2.
        area = "$%d:$%d" % (first_row, last_row)

        # Build up the print titles area "Sheet1!$1:$2"
        sheetname = quote_sheetname(self.name)
        self.repeat_row_range = sheetname + "!" + area

    @convert_column_args
    def repeat_columns(self, first_col, last_col=None):
        """
        Set the columns to repeat at the left hand side of each printed page.

        Args:
            first_col: Start column for range.
            last_col: End column for range.

        Returns:
            Nothing.

        """
        if last_col is None:
            last_col = first_col

        # Convert to A notation.
        first_col = xl_col_to_name(first_col, 1)
        last_col = xl_col_to_name(last_col, 1)

        # Create a column range like $C:$D.
        area = first_col + ":" + last_col

        # Build up the print area range "=Sheet2!$C:$D"
        sheetname = quote_sheetname(self.name)
        self.repeat_col_range = sheetname + "!" + area

    def hide_gridlines(self, option=1):
        """
        Set the option to hide gridlines on the screen and the printed page.

        Args:
            option:    0 : Don't hide gridlines
                       1 : Hide printed gridlines only
                       2 : Hide screen and printed gridlines

        Returns:
            Nothing.

        """
        if option == 0:
            self.print_gridlines = 1
            self.screen_gridlines = 1
            self.print_options_changed = True
        elif option == 1:
            self.print_gridlines = 0
            self.screen_gridlines = 1
        else:
            self.print_gridlines = 0
            self.screen_gridlines = 0

    def print_row_col_headers(self):
        """
        Set the option to print the row and column headers on the printed page.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.print_headers = True
        self.print_options_changed = True

    def hide_row_col_headers(self):
        """
        Set the option to hide the row and column headers on the worksheet.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.row_col_headers = True

    @convert_range_args
    def print_area(self, first_row, first_col, last_row, last_col):
        """
        Set the print area in the current worksheet.

        Args:
            first_row:    The first row of the cell range. (zero indexed).
            first_col:    The first column of the cell range.
            last_row:     The last row of the cell range. (zero indexed).
            last_col:     The last column of the cell range.

        Returns:
            0:  Success.
            -1: Row or column is out of worksheet bounds.

        """
        # Set the print area in the current worksheet.

        # Ignore max print area since it is the same as no  area for Excel.
        if (
            first_row == 0
            and first_col == 0
            and last_row == self.xls_rowmax - 1
            and last_col == self.xls_colmax - 1
        ):
            return

        # Build up the print area range "Sheet1!$A$1:$C$13".
        area = self._convert_name_area(first_row, first_col, last_row, last_col)
        self.print_area_range = area

        return 0

    def print_across(self):
        """
        Set the order in which pages are printed.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.page_order = 1
        self.page_setup_changed = True

    def fit_to_pages(self, width, height):
        """
        Fit the printed area to a specific number of pages both vertically and
        horizontally.

        Args:
            width:  Number of pages horizontally.
            height: Number of pages vertically.

        Returns:
            Nothing.

        """
        self.fit_page = 1
        self.fit_width = width
        self.fit_height = height
        self.page_setup_changed = True

    def set_start_page(self, start_page):
        """
        Set the start page number when printing.

        Args:
            start_page: Start page number.

        Returns:
            Nothing.

        """
        self.page_start = start_page

    def set_print_scale(self, scale):
        """
        Set the scale factor for the printed page.

        Args:
            scale: Print scale. 10 <= scale <= 400.

        Returns:
            Nothing.

        """
        # Confine the scale to Excel's range.
        if scale < 10 or scale > 400:
            warn("Print scale '%d' outside range: 10 <= scale <= 400" % scale)
            return

        # Turn off "fit to page" option when print scale is on.
        self.fit_page = 0

        self.print_scale = int(scale)
        self.page_setup_changed = True

    def print_black_and_white(self):
        """
        Set the option to print the worksheet in black and white.

        Args:
            None.

        Returns:
            Nothing.

        """
        self.black_white = True
        self.page_setup_changed = True

    def set_h_pagebreaks(self, breaks):
        """
        Set the horizontal page breaks on a worksheet.

        Args:
            breaks: List of rows where the page breaks should be added.

        Returns:
            Nothing.

        """
        self.hbreaks = breaks

    def set_v_pagebreaks(self, breaks):
        """
        Set the horizontal page breaks on a worksheet.

        Args:
            breaks: List of columns where the page breaks should be added.

        Returns:
            Nothing.

        """
        self.vbreaks = breaks

    def set_vba_name(self, name=None):
        """
        Set the VBA name for the worksheet. By default this is the
        same as the sheet name: i.e., Sheet1 etc.

        Args:
            name: The VBA name for the worksheet.

        Returns:
            Nothing.

        """
        if name is not None:
            self.vba_codename = name
        else:
            self.vba_codename = "Sheet" + str(self.index + 1)

    def ignore_errors(self, options=None):
        """
        Ignore various Excel errors/warnings in a worksheet for user defined
        ranges.

        Args:
            options: A dict of ignore errors keys with cell range values.

        Returns:
            0: Success.
           -1: Incorrect parameter or option.

        """
        if options is None:
            return -1
        else:
            # Copy the user defined options so they aren't modified.
            options = options.copy()

        # Valid input parameters.
        valid_parameters = {
            "number_stored_as_text",
            "eval_error",
            "formula_differs",
            "formula_range",
            "formula_unlocked",
            "empty_cell_reference",
            "list_data_validation",
            "calculated_column",
            "two_digit_text_year",
        }

        # Check for valid input parameters.
        for param_key in options.keys():
            if param_key not in valid_parameters:
                warn("Unknown parameter '%s' in ignore_errors()" % param_key)
                return -1

        self.ignored_errors = options

        return 0

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################
    def _initialize(self, init_data):
        self.name = init_data["name"]
        self.index = init_data["index"]
        self.str_table = init_data["str_table"]
        self.worksheet_meta = init_data["worksheet_meta"]
        self.constant_memory = init_data["constant_memory"]
        self.tmpdir = init_data["tmpdir"]
        self.date_1904 = init_data["date_1904"]
        self.strings_to_numbers = init_data["strings_to_numbers"]
        self.strings_to_formulas = init_data["strings_to_formulas"]
        self.strings_to_urls = init_data["strings_to_urls"]
        self.nan_inf_to_errors = init_data["nan_inf_to_errors"]
        self.default_date_format = init_data["default_date_format"]
        self.default_url_format = init_data["default_url_format"]
        self.excel2003_style = init_data["excel2003_style"]
        self.remove_timezone = init_data["remove_timezone"]
        self.max_url_length = init_data["max_url_length"]
        self.use_future_functions = init_data["use_future_functions"]

        if self.excel2003_style:
            self.original_row_height = 12.75
            self.default_row_height = 12.75
            self.default_row_pixels = 17
            self.margin_left = 0.75
            self.margin_right = 0.75
            self.margin_top = 1
            self.margin_bottom = 1
            self.margin_header = 0.5
            self.margin_footer = 0.5
            self.header_footer_aligns = False

        # Open a temp filehandle to store row data in constant_memory mode.
        if self.constant_memory:
            # This is sub-optimal but we need to create a temp file
            # with utf8 encoding in Python < 3.
            (fd, filename) = tempfile.mkstemp(dir=self.tmpdir)
            os.close(fd)
            self.row_data_filename = filename
            self.row_data_fh = open(filename, mode="w+", encoding="utf-8")

            # Set as the worksheet filehandle until the file is assembled.
            self.fh = self.row_data_fh

    def _assemble_xml_file(self):
        # Assemble and write the XML file.

        # Write the XML declaration.
        self._xml_declaration()

        # Write the root worksheet element.
        self._write_worksheet()

        # Write the worksheet properties.
        self._write_sheet_pr()

        # Write the worksheet dimensions.
        self._write_dimension()

        # Write the sheet view properties.
        self._write_sheet_views()

        # Write the sheet format properties.
        self._write_sheet_format_pr()

        # Write the sheet column info.
        self._write_cols()

        # Write the worksheet data such as rows columns and cells.
        if not self.constant_memory:
            self._write_sheet_data()
        else:
            self._write_optimized_sheet_data()

        # Write the sheetProtection element.
        self._write_sheet_protection()

        # Write the protectedRanges element.
        self._write_protected_ranges()

        # Write the phoneticPr element.
        if self.excel2003_style:
            self._write_phonetic_pr()

        # Write the autoFilter element.
        self._write_auto_filter()

        # Write the mergeCells element.
        self._write_merge_cells()

        # Write the conditional formats.
        self._write_conditional_formats()

        # Write the dataValidations element.
        self._write_data_validations()

        # Write the hyperlink element.
        self._write_hyperlinks()

        # Write the printOptions element.
        self._write_print_options()

        # Write the worksheet page_margins.
        self._write_page_margins()

        # Write the worksheet page setup.
        self._write_page_setup()

        # Write the headerFooter element.
        self._write_header_footer()

        # Write the rowBreaks element.
        self._write_row_breaks()

        # Write the colBreaks element.
        self._write_col_breaks()

        # Write the ignoredErrors element.
        self._write_ignored_errors()

        # Write the drawing element.
        self._write_drawings()

        # Write the legacyDrawing element.
        self._write_legacy_drawing()

        # Write the legacyDrawingHF element.
        self._write_legacy_drawing_hf()

        # Write the picture element, for the background.
        self._write_picture()

        # Write the tableParts element.
        self._write_table_parts()

        # Write the extLst elements.
        self._write_ext_list()

        # Close the worksheet tag.
        self._xml_end_tag("worksheet")

        # Close the file.
        self._xml_close()

    def _check_dimensions(self, row, col, ignore_row=False, ignore_col=False):
        # Check that row and col are valid and store the max and min
        # values for use in other methods/elements. The ignore_row /
        # ignore_col flags is used to indicate that we wish to perform
        # the dimension check without storing the value. The ignore
        # flags are use by set_row() and data_validate.

        # Check that the row/col are within the worksheet bounds.
        if row < 0 or col < 0:
            return -1
        if row >= self.xls_rowmax or col >= self.xls_colmax:
            return -1

        # In constant_memory mode we don't change dimensions for rows
        # that are already written.
        if not ignore_row and not ignore_col and self.constant_memory:
            if row < self.previous_row:
                return -2

        if not ignore_row:
            if self.dim_rowmin is None or row < self.dim_rowmin:
                self.dim_rowmin = row
            if self.dim_rowmax is None or row > self.dim_rowmax:
                self.dim_rowmax = row

        if not ignore_col:
            if self.dim_colmin is None or col < self.dim_colmin:
                self.dim_colmin = col
            if self.dim_colmax is None or col > self.dim_colmax:
                self.dim_colmax = col

        return 0

    def _convert_date_time(self, dt_obj):
        # Convert a datetime object to an Excel serial date and time.
        return datetime_to_excel_datetime(dt_obj, self.date_1904, self.remove_timezone)

    def _convert_name_area(self, row_num_1, col_num_1, row_num_2, col_num_2):
        # Convert zero indexed rows and columns to the format required by
        # worksheet named ranges, eg, "Sheet1!$A$1:$C$13".

        range1 = ""
        range2 = ""
        area = ""
        row_col_only = 0

        # Convert to A1 notation.
        col_char_1 = xl_col_to_name(col_num_1, 1)
        col_char_2 = xl_col_to_name(col_num_2, 1)
        row_char_1 = "$" + str(row_num_1 + 1)
        row_char_2 = "$" + str(row_num_2 + 1)

        # We need to handle special cases that refer to rows or columns only.
        if row_num_1 == 0 and row_num_2 == self.xls_rowmax - 1:
            range1 = col_char_1
            range2 = col_char_2
            row_col_only = 1
        elif col_num_1 == 0 and col_num_2 == self.xls_colmax - 1:
            range1 = row_char_1
            range2 = row_char_2
            row_col_only = 1
        else:
            range1 = col_char_1 + row_char_1
            range2 = col_char_2 + row_char_2

        # A repeated range is only written once (if it isn't a special case).
        if range1 == range2 and not row_col_only:
            area = range1
        else:
            area = range1 + ":" + range2

        # Build up the print area range "Sheet1!$A$1:$C$13".
        sheetname = quote_sheetname(self.name)
        area = sheetname + "!" + area

        return area

    def _sort_pagebreaks(self, breaks):
        # This is an internal method used to filter elements of a list of
        # pagebreaks used in the _store_hbreak() and _store_vbreak() methods.
        # It:
        #   1. Removes duplicate entries from the list.
        #   2. Sorts the list.
        #   3. Removes 0 from the list if present.
        if not breaks:
            return

        breaks_set = set(breaks)

        if 0 in breaks_set:
            breaks_set.remove(0)

        breaks_list = list(breaks_set)
        breaks_list.sort()

        # The Excel 2007 specification says that the maximum number of page
        # breaks is 1026. However, in practice it is actually 1023.
        max_num_breaks = 1023
        if len(breaks_list) > max_num_breaks:
            breaks_list = breaks_list[:max_num_breaks]

        return breaks_list

    def _extract_filter_tokens(self, expression):
        # Extract the tokens from the filter expression. The tokens are mainly
        # non-whitespace groups. The only tricky part is to extract string
        # tokens that contain whitespace and/or quoted double quotes (Excel's
        # escaped quotes).
        #
        # Examples: 'x <  2000'
        #           'x >  2000 and x <  5000'
        #           'x = "foo"'
        #           'x = "foo bar"'
        #           'x = "foo "" bar"'
        #
        if not expression:
            return []

        token_re = re.compile(r'"(?:[^"]|"")*"|\S+')
        tokens = token_re.findall(expression)

        new_tokens = []
        # Remove single leading and trailing quotes and un-escape other quotes.
        for token in tokens:
            if token.startswith('"'):
                token = token[1:]

            if token.endswith('"'):
                token = token[:-1]

            token = token.replace('""', '"')

            new_tokens.append(token)

        return new_tokens

    def _parse_filter_expression(self, expression, tokens):
        # Converts the tokens of a possibly conditional expression into 1 or 2
        # sub expressions for further parsing.
        #
        # Examples:
        #          ('x', '==', 2000) -> exp1
        #          ('x', '>',  2000, 'and', 'x', '<', 5000) -> exp1 and exp2

        if len(tokens) == 7:
            # The number of tokens will be either 3 (for 1 expression)
            # or 7 (for 2  expressions).
            conditional = tokens[3]

            if re.match("(and|&&)", conditional):
                conditional = 0
            elif re.match(r"(or|\|\|)", conditional):
                conditional = 1
            else:
                warn(
                    "Token '%s' is not a valid conditional "
                    "in filter expression '%s'" % (conditional, expression)
                )

            expression_1 = self._parse_filter_tokens(expression, tokens[0:3])
            expression_2 = self._parse_filter_tokens(expression, tokens[4:7])

            return expression_1 + [conditional] + expression_2
        else:
            return self._parse_filter_tokens(expression, tokens)

    def _parse_filter_tokens(self, expression, tokens):
        # Parse the 3 tokens of a filter expression and return the operator
        # and token. The use of numbers instead of operators is a legacy of
        # Spreadsheet::WriteExcel.
        operators = {
            "==": 2,
            "=": 2,
            "=~": 2,
            "eq": 2,
            "!=": 5,
            "!~": 5,
            "ne": 5,
            "<>": 5,
            "<": 1,
            "<=": 3,
            ">": 4,
            ">=": 6,
        }

        operator = operators.get(tokens[1], None)
        token = tokens[2]

        # Special handling of "Top" filter expressions.
        if re.match("top|bottom", tokens[0].lower()):
            value = int(tokens[1])

            if value < 1 or value > 500:
                warn(
                    "The value '%d' in expression '%s' "
                    "must be in the range 1 to 500" % (value, expression)
                )

            token = token.lower()

            if token != "items" and token != "%":
                warn(
                    "The type '%s' in expression '%s' "
                    "must be either 'items' or '%%'" % (token, expression)
                )

            if tokens[0].lower() == "top":
                operator = 30
            else:
                operator = 32

            if tokens[2] == "%":
                operator += 1

            token = str(value)

        if not operator and tokens[0]:
            warn(
                "Token '%s' is not a valid operator "
                "in filter expression '%s'" % (token[0], expression)
            )

        # Special handling for Blanks/NonBlanks.
        if re.match("blanks|nonblanks", token.lower()):
            # Only allow Equals or NotEqual in this context.
            if operator != 2 and operator != 5:
                warn(
                    "The operator '%s' in expression '%s' "
                    "is not valid in relation to Blanks/NonBlanks'"
                    % (tokens[1], expression)
                )

            token = token.lower()

            # The operator should always be 2 (=) to flag a "simple" equality
            # in the binary record. Therefore we convert <> to =.
            if token == "blanks":
                if operator == 5:
                    token = " "
            else:
                if operator == 5:
                    operator = 2
                    token = "blanks"
                else:
                    operator = 5
                    token = " "

        # if the string token contains an Excel match character then change the
        # operator type to indicate a non "simple" equality.
        if operator == 2 and re.search("[*?]", token):
            operator = 22

        return [operator, token]

    def _encode_password(self, password):
        # Hash a worksheet password. Based on the algorithm in
        # ECMA-376-4:2016, Office Open XML File Formats — Transitional
        # Migration Features, Additional attributes for workbookProtection
        # element (Part 1, §18.2.29).
        hash = 0x0000

        for char in password[::-1]:
            hash = ((hash >> 14) & 0x01) | ((hash << 1) & 0x7FFF)
            hash ^= ord(char)

        hash = ((hash >> 14) & 0x01) | ((hash << 1) & 0x7FFF)
        hash ^= len(password)
        hash ^= 0xCE4B

        return "%X" % hash

    def _prepare_image(
        self,
        index,
        image_id,
        drawing_id,
        width,
        height,
        name,
        image_type,
        x_dpi,
        y_dpi,
        digest,
    ):
        # Set up images/drawings.
        drawing_type = 2
        (
            row,
            col,
            _,
            x_offset,
            y_offset,
            x_scale,
            y_scale,
            url,
            tip,
            anchor,
            _,
            description,
            decorative,
        ) = self.images[index]

        width *= x_scale
        height *= y_scale

        # Scale by non 96dpi resolutions.
        width *= 96.0 / x_dpi
        height *= 96.0 / y_dpi

        dimensions = self._position_object_emus(
            col, row, x_offset, y_offset, width, height, anchor
        )
        # Convert from pixels to emus.
        width = int(0.5 + (width * 9525))
        height = int(0.5 + (height * 9525))

        # Create a Drawing obj to use with worksheet unless one already exists.
        if not self.drawing:
            drawing = Drawing()
            drawing.embedded = 1
            self.drawing = drawing

            self.external_drawing_links.append(
                ["/drawing", "../drawings/drawing" + str(drawing_id) + ".xml", None]
            )
        else:
            drawing = self.drawing

        drawing_object = drawing._add_drawing_object()
        drawing_object["type"] = drawing_type
        drawing_object["dimensions"] = dimensions
        drawing_object["width"] = width
        drawing_object["height"] = height
        drawing_object["description"] = name
        drawing_object["shape"] = None
        drawing_object["anchor"] = anchor
        drawing_object["rel_index"] = 0
        drawing_object["url_rel_index"] = 0
        drawing_object["tip"] = tip
        drawing_object["decorative"] = decorative

        if description is not None:
            drawing_object["description"] = description

        if url:
            target = None
            rel_type = "/hyperlink"
            target_mode = "External"

            if re.match("(ftp|http)s?://", url):
                target = self._escape_url(url)

            if re.match("^mailto:", url):
                target = self._escape_url(url)

            if re.match("external:", url):
                target = url.replace("external:", "")
                target = self._escape_url(target)
                # Additional escape not required in worksheet hyperlinks.
                target = target.replace("#", "%23")

                if re.match(r"\w:", target) or re.match(r"\\", target):
                    target = "file:///" + target
                else:
                    target = target.replace("\\", "/")

            if re.match("internal:", url):
                target = url.replace("internal:", "#")
                target_mode = None

            if target is not None:
                if len(target) > self.max_url_length:
                    warn(
                        "Ignoring URL '%s' with link and/or anchor > %d "
                        "characters since it exceeds Excel's limit for URLS"
                        % (url, self.max_url_length)
                    )
                else:
                    if not self.drawing_rels.get(url):
                        self.drawing_links.append([rel_type, target, target_mode])

                    drawing_object["url_rel_index"] = self._get_drawing_rel_index(url)

        if not self.drawing_rels.get(digest):
            self.drawing_links.append(
                ["/image", "../media/image" + str(image_id) + "." + image_type]
            )

        drawing_object["rel_index"] = self._get_drawing_rel_index(digest)

    def _prepare_shape(self, index, drawing_id):
        # Set up shapes/drawings.
        drawing_type = 3

        (
            row,
            col,
            x_offset,
            y_offset,
            x_scale,
            y_scale,
            text,
            anchor,
            options,
            description,
            decorative,
        ) = self.shapes[index]

        width = options.get("width", self.default_col_pixels * 3)
        height = options.get("height", self.default_row_pixels * 6)

        width *= x_scale
        height *= y_scale

        dimensions = self._position_object_emus(
            col, row, x_offset, y_offset, width, height, anchor
        )

        # Convert from pixels to emus.
        width = int(0.5 + (width * 9525))
        height = int(0.5 + (height * 9525))

        # Create a Drawing obj to use with worksheet unless one already exists.
        if not self.drawing:
            drawing = Drawing()
            drawing.embedded = 1
            self.drawing = drawing

            self.external_drawing_links.append(
                ["/drawing", "../drawings/drawing" + str(drawing_id) + ".xml", None]
            )
        else:
            drawing = self.drawing

        shape = Shape("rect", "TextBox", options)
        shape.text = text

        drawing_object = drawing._add_drawing_object()
        drawing_object["type"] = drawing_type
        drawing_object["dimensions"] = dimensions
        drawing_object["width"] = width
        drawing_object["height"] = height
        drawing_object["description"] = description
        drawing_object["shape"] = shape
        drawing_object["anchor"] = anchor
        drawing_object["rel_index"] = 0
        drawing_object["url_rel_index"] = 0
        drawing_object["tip"] = options.get("tip")
        drawing_object["decorative"] = decorative

        url = options.get("url", None)
        if url:
            target = None
            rel_type = "/hyperlink"
            target_mode = "External"

            if re.match("(ftp|http)s?://", url):
                target = self._escape_url(url)

            if re.match("^mailto:", url):
                target = self._escape_url(url)

            if re.match("external:", url):
                target = url.replace("external:", "file:///")
                target = self._escape_url(target)
                # Additional escape not required in worksheet hyperlinks.
                target = target.replace("#", "%23")

            if re.match("internal:", url):
                target = url.replace("internal:", "#")
                target_mode = None

            if target is not None:
                if len(target) > self.max_url_length:
                    warn(
                        "Ignoring URL '%s' with link and/or anchor > %d "
                        "characters since it exceeds Excel's limit for URLS"
                        % (url, self.max_url_length)
                    )
                else:
                    if not self.drawing_rels.get(url):
                        self.drawing_links.append([rel_type, target, target_mode])

                    drawing_object["url_rel_index"] = self._get_drawing_rel_index(url)

    def _prepare_header_image(
        self, image_id, width, height, name, image_type, position, x_dpi, y_dpi, digest
    ):
        # Set up an image without a drawing object for header/footer images.

        # Strip the extension from the filename.
        name = re.sub(r"\..*$", "", name)

        if not self.vml_drawing_rels.get(digest):
            self.vml_drawing_links.append(
                ["/image", "../media/image" + str(image_id) + "." + image_type]
            )

        ref_id = self._get_vml_drawing_rel_index(digest)

        self.header_images_list.append(
            [width, height, name, position, x_dpi, y_dpi, ref_id]
        )

    def _prepare_background(self, image_id, image_type):
        # Set up an image without a drawing object for backgrounds.
        self.external_background_links.append(
            ["/image", "../media/image" + str(image_id) + "." + image_type]
        )

    def _prepare_chart(self, index, chart_id, drawing_id):
        # Set up chart/drawings.
        drawing_type = 1

        (
            row,
            col,
            chart,
            x_offset,
            y_offset,
            x_scale,
            y_scale,
            anchor,
            description,
            decorative,
        ) = self.charts[index]

        chart.id = chart_id - 1

        # Use user specified dimensions, if any.
        width = int(0.5 + (chart.width * x_scale))
        height = int(0.5 + (chart.height * y_scale))

        dimensions = self._position_object_emus(
            col, row, x_offset, y_offset, width, height, anchor
        )

        # Set the chart name for the embedded object if it has been specified.
        name = chart.chart_name

        # Create a Drawing obj to use with worksheet unless one already exists.
        if not self.drawing:
            drawing = Drawing()
            drawing.embedded = 1
            self.drawing = drawing

            self.external_drawing_links.append(
                ["/drawing", "../drawings/drawing" + str(drawing_id) + ".xml"]
            )
        else:
            drawing = self.drawing

        drawing_object = drawing._add_drawing_object()
        drawing_object["type"] = drawing_type
        drawing_object["dimensions"] = dimensions
        drawing_object["width"] = width
        drawing_object["height"] = height
        drawing_object["name"] = name
        drawing_object["shape"] = None
        drawing_object["anchor"] = anchor
        drawing_object["rel_index"] = self._get_drawing_rel_index()
        drawing_object["url_rel_index"] = 0
        drawing_object["tip"] = None
        drawing_object["description"] = description
        drawing_object["decorative"] = decorative

        self.drawing_links.append(
            ["/chart", "../charts/chart" + str(chart_id) + ".xml"]
        )

    def _position_object_emus(
        self, col_start, row_start, x1, y1, width, height, anchor
    ):
        # Calculate the vertices that define the position of a graphical
        # object within the worksheet in EMUs.
        #
        # The vertices are expressed as English Metric Units (EMUs). There are
        # 12,700 EMUs per point. Therefore, 12,700 * 3 /4 = 9,525 EMUs per
        # pixel
        (
            col_start,
            row_start,
            x1,
            y1,
            col_end,
            row_end,
            x2,
            y2,
            x_abs,
            y_abs,
        ) = self._position_object_pixels(
            col_start, row_start, x1, y1, width, height, anchor
        )

        # Convert the pixel values to EMUs. See above.
        x1 = int(0.5 + 9525 * x1)
        y1 = int(0.5 + 9525 * y1)
        x2 = int(0.5 + 9525 * x2)
        y2 = int(0.5 + 9525 * y2)
        x_abs = int(0.5 + 9525 * x_abs)
        y_abs = int(0.5 + 9525 * y_abs)

        return (col_start, row_start, x1, y1, col_end, row_end, x2, y2, x_abs, y_abs)

    # Calculate the vertices that define the position of a graphical object
    # within the worksheet in pixels.
    #
    #         +------------+------------+
    #         |     A      |      B     |
    #   +-----+------------+------------+
    #   |     |(x1,y1)     |            |
    #   |  1  |(A1)._______|______      |
    #   |     |    |              |     |
    #   |     |    |              |     |
    #   +-----+----|    OBJECT    |-----+
    #   |     |    |              |     |
    #   |  2  |    |______________.     |
    #   |     |            |        (B2)|
    #   |     |            |     (x2,y2)|
    #   +---- +------------+------------+
    #
    # Example of an object that covers some of the area from cell A1 to  B2.
    #
    # Based on the width and height of the object we need to calculate 8 vars:
    #
    #     col_start, row_start, col_end, row_end, x1, y1, x2, y2.
    #
    # We also calculate the absolute x and y position of the top left vertex of
    # the object. This is required for images.
    #
    # The width and height of the cells that the object occupies can be
    # variable and have to be taken into account.
    #
    # The values of col_start and row_start are passed in from the calling
    # function. The values of col_end and row_end are calculated by
    # subtracting the width and height of the object from the width and
    # height of the underlying cells.
    #
    def _position_object_pixels(
        self, col_start, row_start, x1, y1, width, height, anchor
    ):
        # col_start       # Col containing upper left corner of object.
        # x1              # Distance to left side of object.
        #
        # row_start       # Row containing top left corner of object.
        # y1              # Distance to top of object.
        #
        # col_end         # Col containing lower right corner of object.
        # x2              # Distance to right side of object.
        #
        # row_end         # Row containing bottom right corner of object.
        # y2              # Distance to bottom of object.
        #
        # width           # Width of object frame.
        # height          # Height of object frame.
        #
        # x_abs           # Absolute distance to left side of object.
        # y_abs           # Absolute distance to top side of object.
        x_abs = 0
        y_abs = 0

        # Adjust start column for negative offsets.
        while x1 < 0 and col_start > 0:
            x1 += self._size_col(col_start - 1)
            col_start -= 1

        # Adjust start row for negative offsets.
        while y1 < 0 and row_start > 0:
            y1 += self._size_row(row_start - 1)
            row_start -= 1

        # Ensure that the image isn't shifted off the page at top left.
        if x1 < 0:
            x1 = 0

        if y1 < 0:
            y1 = 0

        # Calculate the absolute x offset of the top-left vertex.
        if self.col_size_changed:
            for col_id in range(col_start):
                x_abs += self._size_col(col_id)
        else:
            # Optimization for when the column widths haven't changed.
            x_abs += self.default_col_pixels * col_start

        x_abs += x1

        # Calculate the absolute y offset of the top-left vertex.
        if self.row_size_changed:
            for row_id in range(row_start):
                y_abs += self._size_row(row_id)
        else:
            # Optimization for when the row heights haven't changed.
            y_abs += self.default_row_pixels * row_start

        y_abs += y1

        # Adjust start column for offsets that are greater than the col width.
        while x1 >= self._size_col(col_start, anchor):
            x1 -= self._size_col(col_start)
            col_start += 1

        # Adjust start row for offsets that are greater than the row height.
        while y1 >= self._size_row(row_start, anchor):
            y1 -= self._size_row(row_start)
            row_start += 1

        # Initialize end cell to the same as the start cell.
        col_end = col_start
        row_end = row_start

        # Don't offset the image in the cell if the row/col is hidden.
        if self._size_col(col_start, anchor) > 0:
            width = width + x1
        if self._size_row(row_start, anchor) > 0:
            height = height + y1

        # Subtract the underlying cell widths to find end cell of the object.
        while width >= self._size_col(col_end, anchor):
            width -= self._size_col(col_end, anchor)
            col_end += 1

        # Subtract the underlying cell heights to find end cell of the object.
        while height >= self._size_row(row_end, anchor):
            height -= self._size_row(row_end, anchor)
            row_end += 1

        # The end vertices are whatever is left from the width and height.
        x2 = width
        y2 = height

        return [col_start, row_start, x1, y1, col_end, row_end, x2, y2, x_abs, y_abs]

    def _size_col(self, col, anchor=0):
        # Convert the width of a cell from character units to pixels. Excel
        # rounds the column width to the nearest pixel. If the width hasn't
        # been set by the user we use the default value. A hidden column is
        # treated as having a width of zero unless it has the special
        # "object_position" of 4 (size with cells).
        max_digit_width = 7  # For Calibri 11.
        padding = 5
        pixels = 0

        # Look up the cell value to see if it has been changed.
        if col in self.col_info:
            width = self.col_info[col][0]
            hidden = self.col_info[col][2]

            if width is None:
                width = self.default_col_width

            # Convert to pixels.
            if hidden and anchor != 4:
                pixels = 0
            elif width < 1:
                pixels = int(width * (max_digit_width + padding) + 0.5)
            else:
                pixels = int(width * max_digit_width + 0.5) + padding
        else:
            pixels = self.default_col_pixels

        return pixels

    def _size_row(self, row, anchor=0):
        # Convert the height of a cell from character units to pixels. If the
        # height hasn't been set by the user we use the default value. A
        # hidden row is treated as having a height of zero unless it has the
        # special "object_position" of 4 (size with cells).
        pixels = 0

        # Look up the cell value to see if it has been changed
        if row in self.row_sizes:
            height = self.row_sizes[row][0]
            hidden = self.row_sizes[row][1]

            if hidden and anchor != 4:
                pixels = 0
            else:
                pixels = int(4.0 / 3.0 * height)
        else:
            pixels = int(4.0 / 3.0 * self.default_row_height)

        return pixels

    def _pixels_to_width(self, pixels):
        # Convert the width of a cell from pixels to character units.
        max_digit_width = 7.0  # For Calabri 11.
        padding = 5.0

        if pixels <= 12:
            width = pixels / (max_digit_width + padding)
        else:
            width = (pixels - padding) / max_digit_width

        return width

    def _pixels_to_height(self, pixels):
        # Convert the height of a cell from pixels to character units.
        return 0.75 * pixels

    def _comment_params(self, row, col, string, options):
        # This method handles the additional optional parameters to
        # write_comment() as well as calculating the comment object
        # position and vertices.
        default_width = 128
        default_height = 74
        anchor = 0

        params = {
            "author": None,
            "color": "#ffffe1",
            "start_cell": None,
            "start_col": None,
            "start_row": None,
            "visible": None,
            "width": default_width,
            "height": default_height,
            "x_offset": None,
            "x_scale": 1,
            "y_offset": None,
            "y_scale": 1,
            "font_name": "Tahoma",
            "font_size": 8,
            "font_family": 2,
        }

        # Overwrite the defaults with any user supplied values. Incorrect or
        # misspelled parameters are silently ignored.
        for key in options.keys():
            params[key] = options[key]

        # Ensure that a width and height have been set.
        if not params["width"]:
            params["width"] = default_width
        if not params["height"]:
            params["height"] = default_height

        # Set the comment background color.
        params["color"] = xl_color(params["color"]).lower()

        # Convert from Excel XML style color to XML html style color.
        params["color"] = params["color"].replace("ff", "#", 1)

        # Convert a cell reference to a row and column.
        if params["start_cell"] is not None:
            (start_row, start_col) = xl_cell_to_rowcol(params["start_cell"])
            params["start_row"] = start_row
            params["start_col"] = start_col

        # Set the default start cell and offsets for the comment. These are
        # generally fixed in relation to the parent cell. However there are
        # some edge cases for cells at the, er, edges.
        row_max = self.xls_rowmax
        col_max = self.xls_colmax

        if params["start_row"] is None:
            if row == 0:
                params["start_row"] = 0
            elif row == row_max - 3:
                params["start_row"] = row_max - 7
            elif row == row_max - 2:
                params["start_row"] = row_max - 6
            elif row == row_max - 1:
                params["start_row"] = row_max - 5
            else:
                params["start_row"] = row - 1

        if params["y_offset"] is None:
            if row == 0:
                params["y_offset"] = 2
            elif row == row_max - 3:
                params["y_offset"] = 16
            elif row == row_max - 2:
                params["y_offset"] = 16
            elif row == row_max - 1:
                params["y_offset"] = 14
            else:
                params["y_offset"] = 10

        if params["start_col"] is None:
            if col == col_max - 3:
                params["start_col"] = col_max - 6
            elif col == col_max - 2:
                params["start_col"] = col_max - 5
            elif col == col_max - 1:
                params["start_col"] = col_max - 4
            else:
                params["start_col"] = col + 1

        if params["x_offset"] is None:
            if col == col_max - 3:
                params["x_offset"] = 49
            elif col == col_max - 2:
                params["x_offset"] = 49
            elif col == col_max - 1:
                params["x_offset"] = 49
            else:
                params["x_offset"] = 15

        # Scale the size of the comment box if required.
        if params["x_scale"]:
            params["width"] = params["width"] * params["x_scale"]

        if params["y_scale"]:
            params["height"] = params["height"] * params["y_scale"]

        # Round the dimensions to the nearest pixel.
        params["width"] = int(0.5 + params["width"])
        params["height"] = int(0.5 + params["height"])

        # Calculate the positions of the comment object.
        vertices = self._position_object_pixels(
            params["start_col"],
            params["start_row"],
            params["x_offset"],
            params["y_offset"],
            params["width"],
            params["height"],
            anchor,
        )

        # Add the width and height for VML.
        vertices.append(params["width"])
        vertices.append(params["height"])

        return [
            row,
            col,
            string,
            params["author"],
            params["visible"],
            params["color"],
            params["font_name"],
            params["font_size"],
            params["font_family"],
        ] + [vertices]

    def _button_params(self, row, col, options):
        # This method handles the parameters passed to insert_button() as well
        # as calculating the button object position and vertices.

        default_height = self.default_row_pixels
        default_width = self.default_col_pixels
        anchor = 0

        button_number = 1 + len(self.buttons_list)
        button = {"row": row, "col": col, "font": {}}
        params = {}

        # Overwrite the defaults with any user supplied values. Incorrect or
        # misspelled parameters are silently ignored.
        for key in options.keys():
            params[key] = options[key]

        # Set the button caption.
        caption = params.get("caption")

        # Set a default caption if none was specified by user.
        if caption is None:
            caption = "Button %d" % button_number

        button["font"]["caption"] = caption

        # Set the macro name.
        if params.get("macro"):
            button["macro"] = "[0]!" + params["macro"]
        else:
            button["macro"] = "[0]!Button%d_Click" % button_number

        # Set the alt text for the button.
        button["description"] = params.get("description")

        # Ensure that a width and height have been set.
        params["width"] = params.get("width", default_width)
        params["height"] = params.get("height", default_height)

        # Set the x/y offsets.
        params["x_offset"] = params.get("x_offset", 0)
        params["y_offset"] = params.get("y_offset", 0)

        # Scale the size of the button if required.
        params["width"] = params["width"] * params.get("x_scale", 1)
        params["height"] = params["height"] * params.get("y_scale", 1)

        # Round the dimensions to the nearest pixel.
        params["width"] = int(0.5 + params["width"])
        params["height"] = int(0.5 + params["height"])

        params["start_row"] = row
        params["start_col"] = col

        # Calculate the positions of the button object.
        vertices = self._position_object_pixels(
            params["start_col"],
            params["start_row"],
            params["x_offset"],
            params["y_offset"],
            params["width"],
            params["height"],
            anchor,
        )

        # Add the width and height for VML.
        vertices.append(params["width"])
        vertices.append(params["height"])

        button["vertices"] = vertices

        return button

    def _prepare_vml_objects(
        self, vml_data_id, vml_shape_id, vml_drawing_id, comment_id
    ):
        comments = []
        # Sort the comments into row/column order for easier comparison
        # testing and set the external links for comments and buttons.
        row_nums = sorted(self.comments.keys())

        for row in row_nums:
            col_nums = sorted(self.comments[row].keys())

            for col in col_nums:
                user_options = self.comments[row][col]
                params = self._comment_params(*user_options)
                self.comments[row][col] = params

                # Set comment visibility if required and not user defined.
                if self.comments_visible:
                    if self.comments[row][col][4] is None:
                        self.comments[row][col][4] = 1

                # Set comment author if not already user defined.
                if self.comments[row][col][3] is None:
                    self.comments[row][col][3] = self.comments_author

                comments.append(self.comments[row][col])

        self.external_vml_links.append(
            ["/vmlDrawing", "../drawings/vmlDrawing" + str(vml_drawing_id) + ".vml"]
        )

        if self.has_comments:
            self.comments_list = comments

            self.external_comment_links.append(
                ["/comments", "../comments" + str(comment_id) + ".xml"]
            )

        count = len(comments)
        start_data_id = vml_data_id

        # The VML o:idmap data id contains a comma separated range when there
        # is more than one 1024 block of comments, like this: data="1,2".
        for i in range(int(count / 1024)):
            vml_data_id = "%s,%d" % (vml_data_id, start_data_id + i + 1)

        self.vml_data_id = vml_data_id
        self.vml_shape_id = vml_shape_id

        return count

    def _prepare_header_vml_objects(self, vml_header_id, vml_drawing_id):
        # Set up external linkage for VML header/footer images.

        self.vml_header_id = vml_header_id

        self.external_vml_links.append(
            ["/vmlDrawing", "../drawings/vmlDrawing" + str(vml_drawing_id) + ".vml"]
        )

    def _prepare_tables(self, table_id, seen):
        # Set the table ids for the worksheet tables.
        for table in self.tables:
            table["id"] = table_id

            if table.get("name") is None:
                # Set a default name.
                table["name"] = "Table" + str(table_id)

            # Check for duplicate table names.
            name = table["name"].lower()

            if name in seen:
                raise DuplicateTableName(
                    "Duplicate name '%s' used in worksheet.add_table()." % table["name"]
                )
            else:
                seen[name] = True

            # Store the link used for the rels file.
            self.external_table_links.append(
                ["/table", "../tables/table" + str(table_id) + ".xml"]
            )
            table_id += 1

    def _table_function_to_formula(self, function, col_name):
        # Convert a table total function to a worksheet formula.
        formula = ""

        # Escape special characters, as required by Excel.
        col_name = col_name.replace("'", "''")
        col_name = col_name.replace("#", "'#")
        col_name = col_name.replace("]", "']")
        col_name = col_name.replace("[", "'[")

        subtotals = {
            "average": 101,
            "countNums": 102,
            "count": 103,
            "max": 104,
            "min": 105,
            "stdDev": 107,
            "sum": 109,
            "var": 110,
        }

        if function in subtotals:
            func_num = subtotals[function]
            formula = "SUBTOTAL(%s,[%s])" % (func_num, col_name)
        else:
            warn("Unsupported function '%s' in add_table()" % function)

        return formula

    def _set_spark_color(self, sparkline, options, user_color):
        # Set the sparkline color.
        if user_color not in options:
            return

        sparkline[user_color] = {"rgb": xl_color(options[user_color])}

    def _get_range_data(self, row_start, col_start, row_end, col_end):
        # Returns a range of data from the worksheet _table to be used in
        # chart cached data. Strings are returned as SST ids and decoded
        # in the workbook. Return None for data that doesn't exist since
        # Excel can chart series with data missing.

        if self.constant_memory:
            return ()

        data = []

        # Iterate through the table data.
        for row_num in range(row_start, row_end + 1):
            # Store None if row doesn't exist.
            if row_num not in self.table:
                data.append(None)
                continue

            for col_num in range(col_start, col_end + 1):
                if col_num in self.table[row_num]:
                    cell = self.table[row_num][col_num]

                    cell_type = cell.__class__.__name__

                    if cell_type in ("Number", "Datetime"):
                        # Return a number with Excel's precision.
                        data.append("%.16g" % cell.number)

                    elif cell_type == "String":
                        # Return a string from it's shared string index.
                        index = cell.string
                        string = self.str_table._get_shared_string(index)

                        data.append(string)

                    elif cell_type in ("Formula", "ArrayFormula"):
                        # Return the formula value.
                        value = cell.value

                        if value is None:
                            value = 0

                        data.append(value)

                    elif cell_type == "Blank":
                        # Return a empty cell.
                        data.append("")
                else:
                    # Store None if column doesn't exist.
                    data.append(None)

        return data

    def _csv_join(self, *items):
        # Create a csv string for use with data validation formulas and lists.

        # Convert non string types to string.
        items = [str(item) if not isinstance(item, str) else item for item in items]

        return ",".join(items)

    def _escape_url(self, url):
        # Don't escape URL if it looks already escaped.
        if re.search("%[0-9a-fA-F]{2}", url):
            return url

        # Can't use url.quote() here because it doesn't match Excel.
        url = url.replace("%", "%25")
        url = url.replace('"', "%22")
        url = url.replace(" ", "%20")
        url = url.replace("<", "%3c")
        url = url.replace(">", "%3e")
        url = url.replace("[", "%5b")
        url = url.replace("]", "%5d")
        url = url.replace("^", "%5e")
        url = url.replace("`", "%60")
        url = url.replace("{", "%7b")
        url = url.replace("}", "%7d")

        return url

    def _get_drawing_rel_index(self, target=None):
        # Get the index used to address a drawing rel link.
        if target is None:
            self.drawing_rels_id += 1
            return self.drawing_rels_id
        elif self.drawing_rels.get(target):
            return self.drawing_rels[target]
        else:
            self.drawing_rels_id += 1
            self.drawing_rels[target] = self.drawing_rels_id
            return self.drawing_rels_id

    def _get_vml_drawing_rel_index(self, target=None):
        # Get the index used to address a vml drawing rel link.
        if self.vml_drawing_rels.get(target):
            return self.vml_drawing_rels[target]
        else:
            self.vml_drawing_rels_id += 1
            self.vml_drawing_rels[target] = self.vml_drawing_rels_id
            return self.vml_drawing_rels_id

    ###########################################################################
    #
    # The following font methods are, more or less, duplicated from the
    # Styles class. Not the cleanest version of reuse but works for now.
    #
    ###########################################################################
    def _write_font(self, xf_format):
        # Write the <font> element.
        xml_writer = self.rstring

        xml_writer._xml_start_tag("rPr")

        # Handle the main font properties.
        if xf_format.bold:
            xml_writer._xml_empty_tag("b")
        if xf_format.italic:
            xml_writer._xml_empty_tag("i")
        if xf_format.font_strikeout:
            xml_writer._xml_empty_tag("strike")
        if xf_format.font_outline:
            xml_writer._xml_empty_tag("outline")
        if xf_format.font_shadow:
            xml_writer._xml_empty_tag("shadow")

        # Handle the underline variants.
        if xf_format.underline:
            self._write_underline(xf_format.underline)

        # Handle super/subscript.
        if xf_format.font_script == 1:
            self._write_vert_align("superscript")
        if xf_format.font_script == 2:
            self._write_vert_align("subscript")

        # Write the font size
        xml_writer._xml_empty_tag("sz", [("val", xf_format.font_size)])

        # Handle colors.
        if xf_format.theme == -1:
            # Ignore for excel2003_style.
            pass
        elif xf_format.theme:
            self._write_color("theme", xf_format.theme)
        elif xf_format.color_indexed:
            self._write_color("indexed", xf_format.color_indexed)
        elif xf_format.font_color:
            color = self._get_palette_color(xf_format.font_color)
            self._write_rstring_color("rgb", color)
        else:
            self._write_rstring_color("theme", 1)

        # Write some other font properties related to font families.
        xml_writer._xml_empty_tag("rFont", [("val", xf_format.font_name)])
        xml_writer._xml_empty_tag("family", [("val", xf_format.font_family)])

        if xf_format.font_name == "Calibri" and not xf_format.hyperlink:
            xml_writer._xml_empty_tag("scheme", [("val", xf_format.font_scheme)])

        xml_writer._xml_end_tag("rPr")

    def _write_underline(self, underline):
        # Write the underline font element.
        attributes = []

        # Handle the underline variants.
        if underline == 2:
            attributes = [("val", "double")]
        elif underline == 33:
            attributes = [("val", "singleAccounting")]
        elif underline == 34:
            attributes = [("val", "doubleAccounting")]

        self.rstring._xml_empty_tag("u", attributes)

    def _write_vert_align(self, val):
        # Write the <vertAlign> font sub-element.
        attributes = [("val", val)]

        self.rstring._xml_empty_tag("vertAlign", attributes)

    def _write_rstring_color(self, name, value):
        # Write the <color> element.
        attributes = [(name, value)]

        self.rstring._xml_empty_tag("color", attributes)

    def _get_palette_color(self, color):
        # Convert the RGB color.
        if color[0] == "#":
            color = color[1:]

        return "FF" + color.upper()

    def _opt_close(self):
        # Close the row data filehandle in constant_memory mode.
        if not self.row_data_fh_closed:
            self.row_data_fh.close()
            self.row_data_fh_closed = True

    def _opt_reopen(self):
        # Reopen the row data filehandle in constant_memory mode.
        if self.row_data_fh_closed:
            filename = self.row_data_filename
            self.row_data_fh = open(filename, mode="a+", encoding="utf-8")
            self.row_data_fh_closed = False
            self.fh = self.row_data_fh

    def _set_icon_props(self, total_icons, user_props=None):
        # Set the sub-properties for icons.
        props = []

        # Set the defaults.
        for _ in range(total_icons):
            props.append({"criteria": False, "value": 0, "type": "percent"})

        # Set the default icon values based on the number of icons.
        if total_icons == 3:
            props[0]["value"] = 67
            props[1]["value"] = 33

        if total_icons == 4:
            props[0]["value"] = 75
            props[1]["value"] = 50
            props[2]["value"] = 25

        if total_icons == 5:
            props[0]["value"] = 80
            props[1]["value"] = 60
            props[2]["value"] = 40
            props[3]["value"] = 20

        # Overwrite default properties with user defined properties.
        if user_props:
            # Ensure we don't set user properties for lowest icon.
            max_data = len(user_props)
            if max_data >= total_icons:
                max_data = total_icons - 1

            for i in range(max_data):
                # Set the user defined 'value' property.
                if user_props[i].get("value") is not None:
                    props[i]["value"] = user_props[i]["value"]

                    # Remove the formula '=' sign if it exists.
                    tmp = props[i]["value"]
                    if isinstance(tmp, str) and tmp.startswith("="):
                        props[i]["value"] = tmp.lstrip("=")

                # Set the user defined 'type' property.
                if user_props[i].get("type"):
                    valid_types = ("percent", "percentile", "number", "formula")

                    if user_props[i]["type"] not in valid_types:
                        warn(
                            "Unknown icon property type '%s' for sub-"
                            "property 'type' in conditional_format()"
                            % user_props[i]["type"]
                        )
                    else:
                        props[i]["type"] = user_props[i]["type"]

                        if props[i]["type"] == "number":
                            props[i]["type"] = "num"

                # Set the user defined 'criteria' property.
                criteria = user_props[i].get("criteria")
                if criteria and criteria == ">":
                    props[i]["criteria"] = True

        return props

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_worksheet(self):
        # Write the <worksheet> element. This is the root element.

        schema = "http://schemas.openxmlformats.org/"
        xmlns = schema + "spreadsheetml/2006/main"
        xmlns_r = schema + "officeDocument/2006/relationships"
        xmlns_mc = schema + "markup-compatibility/2006"
        ms_schema = "http://schemas.microsoft.com/"
        xmlns_x14ac = ms_schema + "office/spreadsheetml/2009/9/ac"

        attributes = [("xmlns", xmlns), ("xmlns:r", xmlns_r)]

        # Add some extra attributes for Excel 2010. Mainly for sparklines.
        if self.excel_version == 2010:
            attributes.append(("xmlns:mc", xmlns_mc))
            attributes.append(("xmlns:x14ac", xmlns_x14ac))
            attributes.append(("mc:Ignorable", "x14ac"))

        self._xml_start_tag("worksheet", attributes)

    def _write_dimension(self):
        # Write the <dimension> element. This specifies the range of
        # cells in the worksheet. As a special case, empty
        # spreadsheets use 'A1' as a range.

        if self.dim_rowmin is None and self.dim_colmin is None:
            # If the min dimensions are not defined then no dimensions
            # have been set and we use the default 'A1'.
            ref = "A1"

        elif self.dim_rowmin is None and self.dim_colmin is not None:
            # If the row dimensions aren't set but the column
            # dimensions are set then they have been changed via
            # set_column().

            if self.dim_colmin == self.dim_colmax:
                # The dimensions are a single cell and not a range.
                ref = xl_rowcol_to_cell(0, self.dim_colmin)
            else:
                # The dimensions are a cell range.
                cell_1 = xl_rowcol_to_cell(0, self.dim_colmin)
                cell_2 = xl_rowcol_to_cell(0, self.dim_colmax)
                ref = cell_1 + ":" + cell_2

        elif self.dim_rowmin == self.dim_rowmax and self.dim_colmin == self.dim_colmax:
            # The dimensions are a single cell and not a range.
            ref = xl_rowcol_to_cell(self.dim_rowmin, self.dim_colmin)
        else:
            # The dimensions are a cell range.
            cell_1 = xl_rowcol_to_cell(self.dim_rowmin, self.dim_colmin)
            cell_2 = xl_rowcol_to_cell(self.dim_rowmax, self.dim_colmax)
            ref = cell_1 + ":" + cell_2

        self._xml_empty_tag("dimension", [("ref", ref)])

    def _write_sheet_views(self):
        # Write the <sheetViews> element.
        self._xml_start_tag("sheetViews")

        # Write the sheetView element.
        self._write_sheet_view()

        self._xml_end_tag("sheetViews")

    def _write_sheet_view(self):
        # Write the <sheetViews> element.
        attributes = []

        # Hide screen gridlines if required.
        if not self.screen_gridlines:
            attributes.append(("showGridLines", 0))

        # Hide screen row/column headers.
        if self.row_col_headers:
            attributes.append(("showRowColHeaders", 0))

        # Hide zeroes in cells.
        if not self.show_zeros:
            attributes.append(("showZeros", 0))

        # Display worksheet right to left for Hebrew, Arabic and others.
        if self.is_right_to_left:
            attributes.append(("rightToLeft", 1))

        # Show that the sheet tab is selected.
        if self.selected:
            attributes.append(("tabSelected", 1))

        # Turn outlines off. Also required in the outlinePr element.
        if not self.outline_on:
            attributes.append(("showOutlineSymbols", 0))

        # Set the page view/layout mode if required.
        if self.page_view == 1:
            attributes.append(("view", "pageLayout"))
        elif self.page_view == 2:
            attributes.append(("view", "pageBreakPreview"))

        # Set the first visible cell.
        if self.top_left_cell != "":
            attributes.append(("topLeftCell", self.top_left_cell))

        # Set the zoom level.
        if self.zoom != 100:
            attributes.append(("zoomScale", self.zoom))

            if self.page_view == 0 and self.zoom_scale_normal:
                attributes.append(("zoomScaleNormal", self.zoom))
            if self.page_view == 1:
                attributes.append(("zoomScalePageLayoutView", self.zoom))
            if self.page_view == 2:
                attributes.append(("zoomScaleSheetLayoutView", self.zoom))

        attributes.append(("workbookViewId", 0))

        if self.panes or len(self.selections):
            self._xml_start_tag("sheetView", attributes)
            self._write_panes()
            self._write_selections()
            self._xml_end_tag("sheetView")
        else:
            self._xml_empty_tag("sheetView", attributes)

    def _write_sheet_format_pr(self):
        # Write the <sheetFormatPr> element.
        default_row_height = self.default_row_height
        row_level = self.outline_row_level
        col_level = self.outline_col_level

        attributes = [("defaultRowHeight", default_row_height)]

        if self.default_row_height != self.original_row_height:
            attributes.append(("customHeight", 1))

        if self.default_row_zeroed:
            attributes.append(("zeroHeight", 1))

        if row_level:
            attributes.append(("outlineLevelRow", row_level))
        if col_level:
            attributes.append(("outlineLevelCol", col_level))

        if self.excel_version == 2010:
            attributes.append(("x14ac:dyDescent", "0.25"))

        self._xml_empty_tag("sheetFormatPr", attributes)

    def _write_cols(self):
        # Write the <cols> element and <col> sub elements.

        # Exit unless some column have been formatted.
        if not self.col_info:
            return

        self._xml_start_tag("cols")

        # Use the first element of the column information structures to set
        # the initial/previous properties.
        first_col = (sorted(self.col_info.keys()))[0]
        last_col = first_col
        prev_col_options = self.col_info[first_col]
        del self.col_info[first_col]
        deleted_col = first_col
        deleted_col_options = prev_col_options

        for col in sorted(self.col_info.keys()):
            col_options = self.col_info[col]
            # Check if the column number is contiguous with the previous
            # column and if the properties are the same.
            if col == last_col + 1 and col_options == prev_col_options:
                last_col = col
            else:
                # If not contiguous/equal then we write out the current range
                # of columns and start again.
                self._write_col_info(first_col, last_col, prev_col_options)
                first_col = col
                last_col = first_col
                prev_col_options = col_options

        # We will exit the previous loop with one unhandled column range.
        self._write_col_info(first_col, last_col, prev_col_options)

        # Put back the deleted first column information structure.
        self.col_info[deleted_col] = deleted_col_options

        self._xml_end_tag("cols")

    def _write_col_info(self, col_min, col_max, col_info):
        # Write the <col> element.
        (width, cell_format, hidden, level, collapsed, autofit) = col_info

        custom_width = 1
        xf_index = 0

        # Get the cell_format index.
        if cell_format:
            xf_index = cell_format._get_xf_index()

        # Set the Excel default column width.
        if width is None:
            if not hidden:
                width = 8.43
                custom_width = 0
            else:
                width = 0
        elif width == 8.43:
            # Width is defined but same as default.
            custom_width = 0

        # Convert column width from user units to character width.
        if width > 0:
            # For Calabri 11.
            max_digit_width = 7
            padding = 5

            if width < 1:
                width = (
                    int(
                        (int(width * (max_digit_width + padding) + 0.5))
                        / float(max_digit_width)
                        * 256.0
                    )
                    / 256.0
                )
            else:
                width = (
                    int(
                        (int(width * max_digit_width + 0.5) + padding)
                        / float(max_digit_width)
                        * 256.0
                    )
                    / 256.0
                )

        attributes = [
            ("min", col_min + 1),
            ("max", col_max + 1),
            ("width", "%.16g" % width),
        ]

        if xf_index:
            attributes.append(("style", xf_index))
        if hidden:
            attributes.append(("hidden", "1"))
        if autofit:
            attributes.append(("bestFit", "1"))
        if custom_width:
            attributes.append(("customWidth", "1"))
        if level:
            attributes.append(("outlineLevel", level))
        if collapsed:
            attributes.append(("collapsed", "1"))

        self._xml_empty_tag("col", attributes)

    def _write_sheet_data(self):
        # Write the <sheetData> element.

        if self.dim_rowmin is None:
            # If the dimensions aren't defined there is no data to write.
            self._xml_empty_tag("sheetData")
        else:
            self._xml_start_tag("sheetData")
            self._write_rows()
            self._xml_end_tag("sheetData")

    def _write_optimized_sheet_data(self):
        # Write the <sheetData> element when constant_memory is on. In this
        # case we read the data stored in the temp file and rewrite it to the
        # XML sheet file.
        if self.dim_rowmin is None:
            # If the dimensions aren't defined then there is no data to write.
            self._xml_empty_tag("sheetData")
        else:
            self._xml_start_tag("sheetData")

            # Rewind the filehandle that was used for temp row data.
            buff_size = 65536
            self.row_data_fh.seek(0)
            data = self.row_data_fh.read(buff_size)

            while data:
                self.fh.write(data)
                data = self.row_data_fh.read(buff_size)

            self.row_data_fh.close()
            os.unlink(self.row_data_filename)

            self._xml_end_tag("sheetData")

    def _write_page_margins(self):
        # Write the <pageMargins> element.
        attributes = [
            ("left", self.margin_left),
            ("right", self.margin_right),
            ("top", self.margin_top),
            ("bottom", self.margin_bottom),
            ("header", self.margin_header),
            ("footer", self.margin_footer),
        ]

        self._xml_empty_tag("pageMargins", attributes)

    def _write_page_setup(self):
        # Write the <pageSetup> element.
        #
        # The following is an example taken from Excel.
        #
        # <pageSetup
        #     paperSize="9"
        #     scale="110"
        #     fitToWidth="2"
        #     fitToHeight="2"
        #     pageOrder="overThenDown"
        #     orientation="portrait"
        #     blackAndWhite="1"
        #     draft="1"
        #     horizontalDpi="200"
        #     verticalDpi="200"
        #     r:id="rId1"
        # />
        #
        attributes = []

        # Skip this element if no page setup has changed.
        if not self.page_setup_changed:
            return

        # Set paper size.
        if self.paper_size:
            attributes.append(("paperSize", self.paper_size))

        # Set the print_scale.
        if self.print_scale != 100:
            attributes.append(("scale", self.print_scale))

        # Set the "Fit to page" properties.
        if self.fit_page and self.fit_width != 1:
            attributes.append(("fitToWidth", self.fit_width))

        if self.fit_page and self.fit_height != 1:
            attributes.append(("fitToHeight", self.fit_height))

        # Set the page print direction.
        if self.page_order:
            attributes.append(("pageOrder", "overThenDown"))

        # Set start page for printing.
        if self.page_start > 1:
            attributes.append(("firstPageNumber", self.page_start))

        # Set page orientation.
        if self.orientation:
            attributes.append(("orientation", "portrait"))
        else:
            attributes.append(("orientation", "landscape"))

        # Set the print in black and white option.
        if self.black_white:
            attributes.append(("blackAndWhite", "1"))

        # Set start page for printing.
        if self.page_start != 0:
            attributes.append(("useFirstPageNumber", "1"))

        # Set the DPI. Mainly only for testing.
        if self.is_chartsheet:
            if self.horizontal_dpi:
                attributes.append(("horizontalDpi", self.horizontal_dpi))

            if self.vertical_dpi:
                attributes.append(("verticalDpi", self.vertical_dpi))
        else:
            if self.vertical_dpi:
                attributes.append(("verticalDpi", self.vertical_dpi))

            if self.horizontal_dpi:
                attributes.append(("horizontalDpi", self.horizontal_dpi))

        self._xml_empty_tag("pageSetup", attributes)

    def _write_print_options(self):
        # Write the <printOptions> element.
        attributes = []

        if not self.print_options_changed:
            return

        # Set horizontal centering.
        if self.hcenter:
            attributes.append(("horizontalCentered", 1))

        # Set vertical centering.
        if self.vcenter:
            attributes.append(("verticalCentered", 1))

        # Enable row and column headers.
        if self.print_headers:
            attributes.append(("headings", 1))

        # Set printed gridlines.
        if self.print_gridlines:
            attributes.append(("gridLines", 1))

        self._xml_empty_tag("printOptions", attributes)

    def _write_header_footer(self):
        # Write the <headerFooter> element.
        attributes = []

        if not self.header_footer_scales:
            attributes.append(("scaleWithDoc", 0))

        if not self.header_footer_aligns:
            attributes.append(("alignWithMargins", 0))

        if self.header_footer_changed:
            self._xml_start_tag("headerFooter", attributes)
            if self.header:
                self._write_odd_header()
            if self.footer:
                self._write_odd_footer()
            self._xml_end_tag("headerFooter")
        elif self.excel2003_style:
            self._xml_empty_tag("headerFooter", attributes)

    def _write_odd_header(self):
        # Write the <headerFooter> element.
        self._xml_data_element("oddHeader", self.header)

    def _write_odd_footer(self):
        # Write the <headerFooter> element.
        self._xml_data_element("oddFooter", self.footer)

    def _write_rows(self):
        # Write out the worksheet data as a series of rows and cells.
        self._calculate_spans()

        for row_num in range(self.dim_rowmin, self.dim_rowmax + 1):
            if (
                row_num in self.set_rows
                or row_num in self.comments
                or self.table[row_num]
            ):
                # Only process rows with formatting, cell data and/or comments.

                span_index = int(row_num / 16)

                if span_index in self.row_spans:
                    span = self.row_spans[span_index]
                else:
                    span = None

                if self.table[row_num]:
                    # Write the cells if the row contains data.
                    if row_num not in self.set_rows:
                        self._write_row(row_num, span)
                    else:
                        self._write_row(row_num, span, self.set_rows[row_num])

                    for col_num in range(self.dim_colmin, self.dim_colmax + 1):
                        if col_num in self.table[row_num]:
                            col_ref = self.table[row_num][col_num]
                            self._write_cell(row_num, col_num, col_ref)

                    self._xml_end_tag("row")

                elif row_num in self.comments:
                    # Row with comments in cells.
                    self._write_empty_row(row_num, span, self.set_rows[row_num])
                else:
                    # Blank row with attributes only.
                    self._write_empty_row(row_num, span, self.set_rows[row_num])

    def _write_single_row(self, current_row_num=0):
        # Write out the worksheet data as a single row with cells.
        # This method is used when constant_memory is on. A single
        # row is written and the data table is reset. That way only
        # one row of data is kept in memory at any one time. We don't
        # write span data in the optimized case since it is optional.

        # Set the new previous row as the current row.
        row_num = self.previous_row
        self.previous_row = current_row_num

        if row_num in self.set_rows or row_num in self.comments or self.table[row_num]:
            # Only process rows with formatting, cell data and/or comments.

            # No span data in optimized mode.
            span = None

            if self.table[row_num]:
                # Write the cells if the row contains data.
                if row_num not in self.set_rows:
                    self._write_row(row_num, span)
                else:
                    self._write_row(row_num, span, self.set_rows[row_num])

                for col_num in range(self.dim_colmin, self.dim_colmax + 1):
                    if col_num in self.table[row_num]:
                        col_ref = self.table[row_num][col_num]
                        self._write_cell(row_num, col_num, col_ref)

                self._xml_end_tag("row")
            else:
                # Row attributes or comments only.
                self._write_empty_row(row_num, span, self.set_rows[row_num])

        # Reset table.
        self.table.clear()

    def _calculate_spans(self):
        # Calculate the "spans" attribute of the <row> tag. This is an
        # XLSX optimization and isn't strictly required. However, it
        # makes comparing files easier. The span is the same for each
        # block of 16 rows.
        spans = {}
        span_min = None
        span_max = None

        for row_num in range(self.dim_rowmin, self.dim_rowmax + 1):
            if row_num in self.table:
                # Calculate spans for cell data.
                for col_num in range(self.dim_colmin, self.dim_colmax + 1):
                    if col_num in self.table[row_num]:
                        if span_min is None:
                            span_min = col_num
                            span_max = col_num
                        else:
                            if col_num < span_min:
                                span_min = col_num
                            if col_num > span_max:
                                span_max = col_num

            if row_num in self.comments:
                # Calculate spans for comments.
                for col_num in range(self.dim_colmin, self.dim_colmax + 1):
                    if row_num in self.comments and col_num in self.comments[row_num]:
                        if span_min is None:
                            span_min = col_num
                            span_max = col_num
                        else:
                            if col_num < span_min:
                                span_min = col_num
                            if col_num > span_max:
                                span_max = col_num

            if ((row_num + 1) % 16 == 0) or row_num == self.dim_rowmax:
                span_index = int(row_num / 16)

                if span_min is not None:
                    span_min += 1
                    span_max += 1
                    spans[span_index] = "%s:%s" % (span_min, span_max)
                    span_min = None

        self.row_spans = spans

    def _write_row(self, row, spans, properties=None, empty_row=False):
        # Write the <row> element.
        xf_index = 0

        if properties:
            height, cell_format, hidden, level, collapsed = properties
        else:
            height, cell_format, hidden, level, collapsed = None, None, 0, 0, 0

        if height is None:
            height = self.default_row_height

        attributes = [("r", row + 1)]

        # Get the cell_format index.
        if cell_format:
            xf_index = cell_format._get_xf_index()

        # Add row attributes where applicable.
        if spans:
            attributes.append(("spans", spans))

        if xf_index:
            attributes.append(("s", xf_index))

        if cell_format:
            attributes.append(("customFormat", 1))

        if height != self.original_row_height:
            attributes.append(("ht", "%g" % height))

        if hidden:
            attributes.append(("hidden", 1))

        if height != self.original_row_height:
            attributes.append(("customHeight", 1))

        if level:
            attributes.append(("outlineLevel", level))

        if collapsed:
            attributes.append(("collapsed", 1))

        if self.excel_version == 2010:
            attributes.append(("x14ac:dyDescent", "0.25"))

        if empty_row:
            self._xml_empty_tag_unencoded("row", attributes)
        else:
            self._xml_start_tag_unencoded("row", attributes)

    def _write_empty_row(self, row, spans, properties=None):
        # Write and empty <row> element.
        self._write_row(row, spans, properties, empty_row=True)

    def _write_cell(self, row, col, cell):
        # Write the <cell> element.
        # Note. This is the innermost loop so efficiency is important.

        cell_range = xl_rowcol_to_cell_fast(row, col)
        attributes = [("r", cell_range)]

        if cell.format:
            # Add the cell format index.
            xf_index = cell.format._get_xf_index()
            attributes.append(("s", xf_index))
        elif row in self.set_rows and self.set_rows[row][1]:
            # Add the row format.
            row_xf = self.set_rows[row][1]
            attributes.append(("s", row_xf._get_xf_index()))
        elif col in self.col_info:
            # Add the column format.
            col_xf = self.col_info[col][1]
            if col_xf is not None:
                attributes.append(("s", col_xf._get_xf_index()))

        type_cell_name = cell.__class__.__name__

        # Write the various cell types.
        if type_cell_name in ("Number", "Datetime"):
            # Write a number.
            self._xml_number_element(cell.number, attributes)

        elif type_cell_name in ("String", "RichString"):
            # Write a string.
            string = cell.string

            if not self.constant_memory:
                # Write a shared string.
                self._xml_string_element(string, attributes)
            else:
                # Write an optimized in-line string.

                # Escape control characters. See SharedString.pm for details.
                string = re_control_chars_1.sub(r"_x005F\1", string)
                string = re_control_chars_2.sub(
                    lambda match: "_x%04X_" % ord(match.group(1)), string
                )

                # Escapes non characters in strings.
                string = string.replace("\uFFFE", "_xFFFE_")
                string = string.replace("\uFFFF", "_xFFFF_")

                # Write any rich strings without further tags.
                if string.startswith("<r>") and string.endswith("</r>"):
                    self._xml_rich_inline_string(string, attributes)
                else:
                    # Add attribute to preserve leading or trailing whitespace.
                    preserve = preserve_whitespace(string)
                    self._xml_inline_string(string, preserve, attributes)

        elif type_cell_name == "Formula":
            # Write a formula. First check the formula value type.
            value = cell.value
            if isinstance(cell.value, bool):
                attributes.append(("t", "b"))
                if cell.value:
                    value = 1
                else:
                    value = 0

            elif isinstance(cell.value, str):
                error_codes = (
                    "#DIV/0!",
                    "#N/A",
                    "#NAME?",
                    "#NULL!",
                    "#NUM!",
                    "#REF!",
                    "#VALUE!",
                )

                if cell.value == "":
                    # Allow blank to force recalc in some third party apps.
                    pass
                elif cell.value in error_codes:
                    attributes.append(("t", "e"))
                else:
                    attributes.append(("t", "str"))

            self._xml_formula_element(cell.formula, value, attributes)

        elif type_cell_name == "ArrayFormula":
            # Write a array formula.

            if cell.atype == "dynamic":
                attributes.append(("cm", 1))

            # First check if the formula value is a string.
            try:
                float(cell.value)
            except ValueError:
                attributes.append(("t", "str"))

            # Write an array formula.
            self._xml_start_tag("c", attributes)

            self._write_cell_array_formula(cell.formula, cell.range)
            self._write_cell_value(cell.value)
            self._xml_end_tag("c")

        elif type_cell_name == "Blank":
            # Write a empty cell.
            self._xml_empty_tag("c", attributes)

        elif type_cell_name == "Boolean":
            # Write a boolean cell.
            attributes.append(("t", "b"))
            self._xml_start_tag("c", attributes)
            self._write_cell_value(cell.boolean)
            self._xml_end_tag("c")

    def _write_cell_value(self, value):
        # Write the cell value <v> element.
        if value is None:
            value = ""

        self._xml_data_element("v", value)

    def _write_cell_array_formula(self, formula, cell_range):
        # Write the cell array formula <f> element.
        attributes = [("t", "array"), ("ref", cell_range)]

        self._xml_data_element("f", formula, attributes)

    def _write_sheet_pr(self):
        # Write the <sheetPr> element for Sheet level properties.
        attributes = []

        if (
            not self.fit_page
            and not self.filter_on
            and not self.tab_color
            and not self.outline_changed
            and not self.vba_codename
        ):
            return

        if self.vba_codename:
            attributes.append(("codeName", self.vba_codename))

        if self.filter_on:
            attributes.append(("filterMode", 1))

        if self.fit_page or self.tab_color or self.outline_changed:
            self._xml_start_tag("sheetPr", attributes)
            self._write_tab_color()
            self._write_outline_pr()
            self._write_page_set_up_pr()
            self._xml_end_tag("sheetPr")
        else:
            self._xml_empty_tag("sheetPr", attributes)

    def _write_page_set_up_pr(self):
        # Write the <pageSetUpPr> element.
        if not self.fit_page:
            return

        attributes = [("fitToPage", 1)]
        self._xml_empty_tag("pageSetUpPr", attributes)

    def _write_tab_color(self):
        # Write the <tabColor> element.
        color = self.tab_color

        if not color:
            return

        attributes = [("rgb", color)]

        self._xml_empty_tag("tabColor", attributes)

    def _write_outline_pr(self):
        # Write the <outlinePr> element.
        attributes = []

        if not self.outline_changed:
            return

        if self.outline_style:
            attributes.append(("applyStyles", 1))
        if not self.outline_below:
            attributes.append(("summaryBelow", 0))
        if not self.outline_right:
            attributes.append(("summaryRight", 0))
        if not self.outline_on:
            attributes.append(("showOutlineSymbols", 0))

        self._xml_empty_tag("outlinePr", attributes)

    def _write_row_breaks(self):
        # Write the <rowBreaks> element.
        page_breaks = self._sort_pagebreaks(self.hbreaks)

        if not page_breaks:
            return

        count = len(page_breaks)

        attributes = [
            ("count", count),
            ("manualBreakCount", count),
        ]

        self._xml_start_tag("rowBreaks", attributes)

        for row_num in page_breaks:
            self._write_brk(row_num, 16383)

        self._xml_end_tag("rowBreaks")

    def _write_col_breaks(self):
        # Write the <colBreaks> element.
        page_breaks = self._sort_pagebreaks(self.vbreaks)

        if not page_breaks:
            return

        count = len(page_breaks)

        attributes = [
            ("count", count),
            ("manualBreakCount", count),
        ]

        self._xml_start_tag("colBreaks", attributes)

        for col_num in page_breaks:
            self._write_brk(col_num, 1048575)

        self._xml_end_tag("colBreaks")

    def _write_brk(self, brk_id, brk_max):
        # Write the <brk> element.
        attributes = [("id", brk_id), ("max", brk_max), ("man", 1)]

        self._xml_empty_tag("brk", attributes)

    def _write_merge_cells(self):
        # Write the <mergeCells> element.
        merged_cells = self.merge
        count = len(merged_cells)

        if not count:
            return

        attributes = [("count", count)]

        self._xml_start_tag("mergeCells", attributes)

        for merged_range in merged_cells:
            # Write the mergeCell element.
            self._write_merge_cell(merged_range)

        self._xml_end_tag("mergeCells")

    def _write_merge_cell(self, merged_range):
        # Write the <mergeCell> element.
        (row_min, col_min, row_max, col_max) = merged_range

        # Convert the merge dimensions to a cell range.
        cell_1 = xl_rowcol_to_cell(row_min, col_min)
        cell_2 = xl_rowcol_to_cell(row_max, col_max)
        ref = cell_1 + ":" + cell_2

        attributes = [("ref", ref)]

        self._xml_empty_tag("mergeCell", attributes)

    def _write_hyperlinks(self):
        # Process any stored hyperlinks in row/col order and write the
        # <hyperlinks> element. The attributes are different for internal
        # and external links.
        hlink_refs = []
        display = None

        # Sort the hyperlinks into row order.
        row_nums = sorted(self.hyperlinks.keys())

        # Exit if there are no hyperlinks to process.
        if not row_nums:
            return

        # Iterate over the rows.
        for row_num in row_nums:
            # Sort the hyperlinks into column order.
            col_nums = sorted(self.hyperlinks[row_num].keys())

            # Iterate over the columns.
            for col_num in col_nums:
                # Get the link data for this cell.
                link = self.hyperlinks[row_num][col_num]
                link_type = link["link_type"]

                # If the cell isn't a string then we have to add the url as
                # the string to display.
                if self.table and self.table[row_num] and self.table[row_num][col_num]:
                    cell = self.table[row_num][col_num]
                    if cell.__class__.__name__ != "String":
                        display = link["url"]

                if link_type == 1:
                    # External link with rel file relationship.
                    self.rel_count += 1

                    hlink_refs.append(
                        [
                            link_type,
                            row_num,
                            col_num,
                            self.rel_count,
                            link["str"],
                            display,
                            link["tip"],
                        ]
                    )

                    # Links for use by the packager.
                    self.external_hyper_links.append(
                        ["/hyperlink", link["url"], "External"]
                    )
                else:
                    # Internal link with rel file relationship.
                    hlink_refs.append(
                        [
                            link_type,
                            row_num,
                            col_num,
                            link["url"],
                            link["str"],
                            link["tip"],
                        ]
                    )

        # Write the hyperlink elements.
        self._xml_start_tag("hyperlinks")

        for args in hlink_refs:
            link_type = args.pop(0)

            if link_type == 1:
                self._write_hyperlink_external(*args)
            elif link_type == 2:
                self._write_hyperlink_internal(*args)

        self._xml_end_tag("hyperlinks")

    def _write_hyperlink_external(
        self, row, col, id_num, location=None, display=None, tooltip=None
    ):
        # Write the <hyperlink> element for external links.
        ref = xl_rowcol_to_cell(row, col)
        r_id = "rId" + str(id_num)

        attributes = [("ref", ref), ("r:id", r_id)]

        if location is not None:
            attributes.append(("location", location))
        if display is not None:
            attributes.append(("display", display))
        if tooltip is not None:
            attributes.append(("tooltip", tooltip))

        self._xml_empty_tag("hyperlink", attributes)

    def _write_hyperlink_internal(
        self, row, col, location=None, display=None, tooltip=None
    ):
        # Write the <hyperlink> element for internal links.
        ref = xl_rowcol_to_cell(row, col)

        attributes = [("ref", ref), ("location", location)]

        if tooltip is not None:
            attributes.append(("tooltip", tooltip))
        attributes.append(("display", display))

        self._xml_empty_tag("hyperlink", attributes)

    def _write_auto_filter(self):
        # Write the <autoFilter> element.
        if not self.autofilter_ref:
            return

        attributes = [("ref", self.autofilter_ref)]

        if self.filter_on:
            # Autofilter defined active filters.
            self._xml_start_tag("autoFilter", attributes)
            self._write_autofilters()
            self._xml_end_tag("autoFilter")

        else:
            # Autofilter defined without active filters.
            self._xml_empty_tag("autoFilter", attributes)

    def _write_autofilters(self):
        # Function to iterate through the columns that form part of an
        # autofilter range and write the appropriate filters.
        (col1, col2) = self.filter_range

        for col in range(col1, col2 + 1):
            # Skip if column doesn't have an active filter.
            if col not in self.filter_cols:
                continue

            # Retrieve the filter tokens and write the autofilter records.
            tokens = self.filter_cols[col]
            filter_type = self.filter_type[col]

            # Filters are relative to first column in the autofilter.
            self._write_filter_column(col - col1, filter_type, tokens)

    def _write_filter_column(self, col_id, filter_type, filters):
        # Write the <filterColumn> element.
        attributes = [("colId", col_id)]

        self._xml_start_tag("filterColumn", attributes)

        if filter_type == 1:
            # Type == 1 is the new XLSX style filter.
            self._write_filters(filters)
        else:
            # Type == 0 is the classic "custom" filter.
            self._write_custom_filters(filters)

        self._xml_end_tag("filterColumn")

    def _write_filters(self, filters):
        # Write the <filters> element.
        non_blanks = [filter for filter in filters if str(filter).lower() != "blanks"]
        attributes = []

        if len(filters) != len(non_blanks):
            attributes = [("blank", 1)]

        if len(filters) == 1 and len(non_blanks) == 0:
            # Special case for blank cells only.
            self._xml_empty_tag("filters", attributes)
        else:
            # General case.
            self._xml_start_tag("filters", attributes)

            for autofilter in sorted(non_blanks):
                self._write_filter(autofilter)

            self._xml_end_tag("filters")

    def _write_filter(self, val):
        # Write the <filter> element.
        attributes = [("val", val)]

        self._xml_empty_tag("filter", attributes)

    def _write_custom_filters(self, tokens):
        # Write the <customFilters> element.
        if len(tokens) == 2:
            # One filter expression only.
            self._xml_start_tag("customFilters")
            self._write_custom_filter(*tokens)
            self._xml_end_tag("customFilters")
        else:
            # Two filter expressions.
            attributes = []

            # Check if the "join" operand is "and" or "or".
            if tokens[2] == 0:
                attributes = [("and", 1)]
            else:
                attributes = [("and", 0)]

            # Write the two custom filters.
            self._xml_start_tag("customFilters", attributes)
            self._write_custom_filter(tokens[0], tokens[1])
            self._write_custom_filter(tokens[3], tokens[4])
            self._xml_end_tag("customFilters")

    def _write_custom_filter(self, operator, val):
        # Write the <customFilter> element.
        attributes = []

        operators = {
            1: "lessThan",
            2: "equal",
            3: "lessThanOrEqual",
            4: "greaterThan",
            5: "notEqual",
            6: "greaterThanOrEqual",
            22: "equal",
        }

        # Convert the operator from a number to a descriptive string.
        if operators[operator] is not None:
            operator = operators[operator]
        else:
            warn("Unknown operator = %s" % operator)

        # The 'equal' operator is the default attribute and isn't stored.
        if operator != "equal":
            attributes.append(("operator", operator))
        attributes.append(("val", val))

        self._xml_empty_tag("customFilter", attributes)

    def _write_sheet_protection(self):
        # Write the <sheetProtection> element.
        attributes = []

        if not self.protect_options:
            return

        options = self.protect_options

        if options["password"]:
            attributes.append(("password", options["password"]))
        if options["sheet"]:
            attributes.append(("sheet", 1))
        if options["content"]:
            attributes.append(("content", 1))
        if not options["objects"]:
            attributes.append(("objects", 1))
        if not options["scenarios"]:
            attributes.append(("scenarios", 1))
        if options["format_cells"]:
            attributes.append(("formatCells", 0))
        if options["format_columns"]:
            attributes.append(("formatColumns", 0))
        if options["format_rows"]:
            attributes.append(("formatRows", 0))
        if options["insert_columns"]:
            attributes.append(("insertColumns", 0))
        if options["insert_rows"]:
            attributes.append(("insertRows", 0))
        if options["insert_hyperlinks"]:
            attributes.append(("insertHyperlinks", 0))
        if options["delete_columns"]:
            attributes.append(("deleteColumns", 0))
        if options["delete_rows"]:
            attributes.append(("deleteRows", 0))
        if not options["select_locked_cells"]:
            attributes.append(("selectLockedCells", 1))
        if options["sort"]:
            attributes.append(("sort", 0))
        if options["autofilter"]:
            attributes.append(("autoFilter", 0))
        if options["pivot_tables"]:
            attributes.append(("pivotTables", 0))
        if not options["select_unlocked_cells"]:
            attributes.append(("selectUnlockedCells", 1))

        self._xml_empty_tag("sheetProtection", attributes)

    def _write_protected_ranges(self):
        # Write the <protectedRanges> element.
        if self.num_protected_ranges == 0:
            return

        self._xml_start_tag("protectedRanges")

        for cell_range, range_name, password in self.protected_ranges:
            self._write_protected_range(cell_range, range_name, password)

        self._xml_end_tag("protectedRanges")

    def _write_protected_range(self, cell_range, range_name, password):
        # Write the <protectedRange> element.
        attributes = []

        if password:
            attributes.append(("password", password))

        attributes.append(("sqref", cell_range))
        attributes.append(("name", range_name))

        self._xml_empty_tag("protectedRange", attributes)

    def _write_drawings(self):
        # Write the <drawing> elements.
        if not self.drawing:
            return

        self.rel_count += 1
        self._write_drawing(self.rel_count)

    def _write_drawing(self, drawing_id):
        # Write the <drawing> element.
        r_id = "rId" + str(drawing_id)

        attributes = [("r:id", r_id)]

        self._xml_empty_tag("drawing", attributes)

    def _write_legacy_drawing(self):
        # Write the <legacyDrawing> element.
        if not self.has_vml:
            return

        # Increment the relationship id for any drawings or comments.
        self.rel_count += 1
        r_id = "rId" + str(self.rel_count)

        attributes = [("r:id", r_id)]

        self._xml_empty_tag("legacyDrawing", attributes)

    def _write_legacy_drawing_hf(self):
        # Write the <legacyDrawingHF> element.
        if not self.has_header_vml:
            return

        # Increment the relationship id for any drawings or comments.
        self.rel_count += 1
        r_id = "rId" + str(self.rel_count)

        attributes = [("r:id", r_id)]

        self._xml_empty_tag("legacyDrawingHF", attributes)

    def _write_picture(self):
        # Write the <picture> element.
        if not self.background_image:
            return

        # Increment the relationship id.
        self.rel_count += 1
        r_id = "rId" + str(self.rel_count)

        attributes = [("r:id", r_id)]

        self._xml_empty_tag("picture", attributes)

    def _write_data_validations(self):
        # Write the <dataValidations> element.
        validations = self.validations
        count = len(validations)

        if not count:
            return

        attributes = [("count", count)]

        self._xml_start_tag("dataValidations", attributes)

        for validation in validations:
            # Write the dataValidation element.
            self._write_data_validation(validation)

        self._xml_end_tag("dataValidations")

    def _write_data_validation(self, options):
        # Write the <dataValidation> element.
        sqref = ""
        attributes = []

        # Set the cell range(s) for the data validation.
        for cells in options["cells"]:
            # Add a space between multiple cell ranges.
            if sqref != "":
                sqref += " "

            (row_first, col_first, row_last, col_last) = cells

            # Swap last row/col for first row/col as necessary
            if row_first > row_last:
                (row_first, row_last) = (row_last, row_first)

            if col_first > col_last:
                (col_first, col_last) = (col_last, col_first)

            sqref += xl_range(row_first, col_first, row_last, col_last)

        if options.get("multi_range"):
            sqref = options["multi_range"]

        if options["validate"] != "none":
            attributes.append(("type", options["validate"]))

            if options["criteria"] != "between":
                attributes.append(("operator", options["criteria"]))

        if "error_type" in options:
            if options["error_type"] == 1:
                attributes.append(("errorStyle", "warning"))
            if options["error_type"] == 2:
                attributes.append(("errorStyle", "information"))

        if options["ignore_blank"]:
            attributes.append(("allowBlank", 1))

        if not options["dropdown"]:
            attributes.append(("showDropDown", 1))

        if options["show_input"]:
            attributes.append(("showInputMessage", 1))

        if options["show_error"]:
            attributes.append(("showErrorMessage", 1))

        if "error_title" in options:
            attributes.append(("errorTitle", options["error_title"]))

        if "error_message" in options:
            attributes.append(("error", options["error_message"]))

        if "input_title" in options:
            attributes.append(("promptTitle", options["input_title"]))

        if "input_message" in options:
            attributes.append(("prompt", options["input_message"]))

        attributes.append(("sqref", sqref))

        if options["validate"] == "none":
            self._xml_empty_tag("dataValidation", attributes)
        else:
            self._xml_start_tag("dataValidation", attributes)

            # Write the formula1 element.
            self._write_formula_1(options["value"])

            # Write the formula2 element.
            if options["maximum"] is not None:
                self._write_formula_2(options["maximum"])

            self._xml_end_tag("dataValidation")

    def _write_formula_1(self, formula):
        # Write the <formula1> element.

        if isinstance(formula, list):
            formula = self._csv_join(*formula)
            formula = '"%s"' % formula
        else:
            # Check if the formula is a number.
            try:
                float(formula)
            except ValueError:
                # Not a number. Remove the formula '=' sign if it exists.
                if formula.startswith("="):
                    formula = formula.lstrip("=")

        self._xml_data_element("formula1", formula)

    def _write_formula_2(self, formula):
        # Write the <formula2> element.

        # Check if the formula is a number.
        try:
            float(formula)
        except ValueError:
            # Not a number. Remove the formula '=' sign if it exists.
            if formula.startswith("="):
                formula = formula.lstrip("=")

        self._xml_data_element("formula2", formula)

    def _write_conditional_formats(self):
        # Write the Worksheet conditional formats.
        ranges = sorted(self.cond_formats.keys())

        if not ranges:
            return

        for cond_range in ranges:
            self._write_conditional_formatting(
                cond_range, self.cond_formats[cond_range]
            )

    def _write_conditional_formatting(self, cond_range, params):
        # Write the <conditionalFormatting> element.
        attributes = [("sqref", cond_range)]
        self._xml_start_tag("conditionalFormatting", attributes)
        for param in params:
            # Write the cfRule element.
            self._write_cf_rule(param)
        self._xml_end_tag("conditionalFormatting")

    def _write_cf_rule(self, params):
        # Write the <cfRule> element.
        attributes = [("type", params["type"])]

        if "format" in params and params["format"] is not None:
            attributes.append(("dxfId", params["format"]))

        attributes.append(("priority", params["priority"]))

        if params.get("stop_if_true"):
            attributes.append(("stopIfTrue", 1))

        if params["type"] == "cellIs":
            attributes.append(("operator", params["criteria"]))

            self._xml_start_tag("cfRule", attributes)

            if "minimum" in params and "maximum" in params:
                self._write_formula_element(params["minimum"])
                self._write_formula_element(params["maximum"])
            else:
                self._write_formula_element(params["value"])

            self._xml_end_tag("cfRule")

        elif params["type"] == "aboveAverage":
            if re.search("below", params["criteria"]):
                attributes.append(("aboveAverage", 0))

            if re.search("equal", params["criteria"]):
                attributes.append(("equalAverage", 1))

            if re.search("[123] std dev", params["criteria"]):
                match = re.search("([123]) std dev", params["criteria"])
                attributes.append(("stdDev", match.group(1)))

            self._xml_empty_tag("cfRule", attributes)

        elif params["type"] == "top10":
            if "criteria" in params and params["criteria"] == "%":
                attributes.append(("percent", 1))

            if "direction" in params:
                attributes.append(("bottom", 1))

            rank = params["value"] or 10
            attributes.append(("rank", rank))

            self._xml_empty_tag("cfRule", attributes)

        elif params["type"] == "duplicateValues":
            self._xml_empty_tag("cfRule", attributes)

        elif params["type"] == "uniqueValues":
            self._xml_empty_tag("cfRule", attributes)

        elif (
            params["type"] == "containsText"
            or params["type"] == "notContainsText"
            or params["type"] == "beginsWith"
            or params["type"] == "endsWith"
        ):
            attributes.append(("operator", params["criteria"]))
            attributes.append(("text", params["value"]))
            self._xml_start_tag("cfRule", attributes)
            self._write_formula_element(params["formula"])
            self._xml_end_tag("cfRule")

        elif params["type"] == "timePeriod":
            attributes.append(("timePeriod", params["criteria"]))
            self._xml_start_tag("cfRule", attributes)
            self._write_formula_element(params["formula"])
            self._xml_end_tag("cfRule")

        elif (
            params["type"] == "containsBlanks"
            or params["type"] == "notContainsBlanks"
            or params["type"] == "containsErrors"
            or params["type"] == "notContainsErrors"
        ):
            self._xml_start_tag("cfRule", attributes)
            self._write_formula_element(params["formula"])
            self._xml_end_tag("cfRule")

        elif params["type"] == "colorScale":
            self._xml_start_tag("cfRule", attributes)
            self._write_color_scale(params)
            self._xml_end_tag("cfRule")

        elif params["type"] == "dataBar":
            self._xml_start_tag("cfRule", attributes)
            self._write_data_bar(params)

            if params.get("is_data_bar_2010"):
                self._write_data_bar_ext(params)

            self._xml_end_tag("cfRule")

        elif params["type"] == "expression":
            self._xml_start_tag("cfRule", attributes)
            self._write_formula_element(params["criteria"])
            self._xml_end_tag("cfRule")

        elif params["type"] == "iconSet":
            self._xml_start_tag("cfRule", attributes)
            self._write_icon_set(params)
            self._xml_end_tag("cfRule")

    def _write_formula_element(self, formula):
        # Write the <formula> element.

        # Check if the formula is a number.
        try:
            float(formula)
        except ValueError:
            # Not a number. Remove the formula '=' sign if it exists.
            if formula.startswith("="):
                formula = formula.lstrip("=")

        self._xml_data_element("formula", formula)

    def _write_color_scale(self, param):
        # Write the <colorScale> element.

        self._xml_start_tag("colorScale")

        self._write_cfvo(param["min_type"], param["min_value"])

        if param["mid_type"] is not None:
            self._write_cfvo(param["mid_type"], param["mid_value"])

        self._write_cfvo(param["max_type"], param["max_value"])

        self._write_color("rgb", param["min_color"])

        if param["mid_color"] is not None:
            self._write_color("rgb", param["mid_color"])

        self._write_color("rgb", param["max_color"])

        self._xml_end_tag("colorScale")

    def _write_data_bar(self, param):
        # Write the <dataBar> element.
        attributes = []

        # Min and max bar lengths in in the spec but not supported directly by
        # Excel.
        if param.get("min_length"):
            attributes.append(("minLength", param["min_length"]))

        if param.get("max_length"):
            attributes.append(("maxLength", param["max_length"]))

        if param.get("bar_only"):
            attributes.append(("showValue", 0))

        self._xml_start_tag("dataBar", attributes)

        self._write_cfvo(param["min_type"], param["min_value"])
        self._write_cfvo(param["max_type"], param["max_value"])
        self._write_color("rgb", param["bar_color"])

        self._xml_end_tag("dataBar")

    def _write_data_bar_ext(self, param):
        # Write the <extLst> dataBar extension element.

        # Create a pseudo GUID for each unique Excel 2010 data bar.
        worksheet_count = self.index + 1
        data_bar_count = len(self.data_bars_2010) + 1
        guid = "{DA7ABA51-AAAA-BBBB-%04X-%012X}" % (worksheet_count, data_bar_count)

        # Store the 2010 data bar parameters to write the extLst elements.
        param["guid"] = guid
        self.data_bars_2010.append(param)

        self._xml_start_tag("extLst")
        self._write_ext("{B025F937-C7B1-47D3-B67F-A62EFF666E3E}")
        self._xml_data_element("x14:id", guid)
        self._xml_end_tag("ext")
        self._xml_end_tag("extLst")

    def _write_icon_set(self, param):
        # Write the <iconSet> element.
        attributes = []

        # Don't set attribute for default style.
        if param["icon_style"] != "3TrafficLights":
            attributes = [("iconSet", param["icon_style"])]

        if param.get("icons_only"):
            attributes.append(("showValue", 0))

        if param.get("reverse_icons"):
            attributes.append(("reverse", 1))

        self._xml_start_tag("iconSet", attributes)

        # Write the properties for different icon styles.
        for icon in reversed(param["icons"]):
            self._write_cfvo(icon["type"], icon["value"], icon["criteria"])

        self._xml_end_tag("iconSet")

    def _write_cfvo(self, cf_type, val, criteria=None):
        # Write the <cfvo> element.
        attributes = [("type", cf_type)]

        if val is not None:
            attributes.append(("val", val))

        if criteria:
            attributes.append(("gte", 0))

        self._xml_empty_tag("cfvo", attributes)

    def _write_color(self, name, value):
        # Write the <color> element.
        attributes = [(name, value)]

        self._xml_empty_tag("color", attributes)

    def _write_selections(self):
        # Write the <selection> elements.
        for selection in self.selections:
            self._write_selection(*selection)

    def _write_selection(self, pane, active_cell, sqref):
        # Write the <selection> element.
        attributes = []

        if pane:
            attributes.append(("pane", pane))

        if active_cell:
            attributes.append(("activeCell", active_cell))

        if sqref:
            attributes.append(("sqref", sqref))

        self._xml_empty_tag("selection", attributes)

    def _write_panes(self):
        # Write the frozen or split <pane> elements.
        panes = self.panes

        if not len(panes):
            return

        if panes[4] == 2:
            self._write_split_panes(*panes)
        else:
            self._write_freeze_panes(*panes)

    def _write_freeze_panes(self, row, col, top_row, left_col, pane_type):
        # Write the <pane> element for freeze panes.
        attributes = []

        y_split = row
        x_split = col
        top_left_cell = xl_rowcol_to_cell(top_row, left_col)
        active_pane = ""
        state = ""
        active_cell = ""
        sqref = ""

        # Move user cell selection to the panes.
        if self.selections:
            (_, active_cell, sqref) = self.selections[0]
            self.selections = []

        # Set the active pane.
        if row and col:
            active_pane = "bottomRight"

            row_cell = xl_rowcol_to_cell(row, 0)
            col_cell = xl_rowcol_to_cell(0, col)

            self.selections.append(["topRight", col_cell, col_cell])
            self.selections.append(["bottomLeft", row_cell, row_cell])
            self.selections.append(["bottomRight", active_cell, sqref])

        elif col:
            active_pane = "topRight"
            self.selections.append(["topRight", active_cell, sqref])

        else:
            active_pane = "bottomLeft"
            self.selections.append(["bottomLeft", active_cell, sqref])

        # Set the pane type.
        if pane_type == 0:
            state = "frozen"
        elif pane_type == 1:
            state = "frozenSplit"
        else:
            state = "split"

        if x_split:
            attributes.append(("xSplit", x_split))

        if y_split:
            attributes.append(("ySplit", y_split))

        attributes.append(("topLeftCell", top_left_cell))
        attributes.append(("activePane", active_pane))
        attributes.append(("state", state))

        self._xml_empty_tag("pane", attributes)

    def _write_split_panes(self, row, col, top_row, left_col, pane_type):
        # Write the <pane> element for split panes.
        attributes = []
        has_selection = 0
        active_pane = ""
        active_cell = ""
        sqref = ""

        y_split = row
        x_split = col

        # Move user cell selection to the panes.
        if self.selections:
            (_, active_cell, sqref) = self.selections[0]
            self.selections = []
            has_selection = 1

        # Convert the row and col to 1/20 twip units with padding.
        if y_split:
            y_split = int(20 * y_split + 300)

        if x_split:
            x_split = self._calculate_x_split_width(x_split)

        # For non-explicit topLeft definitions, estimate the cell offset based
        # on the pixels dimensions. This is only a workaround and doesn't take
        # adjusted cell dimensions into account.
        if top_row == row and left_col == col:
            top_row = int(0.5 + (y_split - 300) / 20 / 15)
            left_col = int(0.5 + (x_split - 390) / 20 / 3 * 4 / 64)

        top_left_cell = xl_rowcol_to_cell(top_row, left_col)

        # If there is no selection set the active cell to the top left cell.
        if not has_selection:
            active_cell = top_left_cell
            sqref = top_left_cell

        # Set the Cell selections.
        if row and col:
            active_pane = "bottomRight"

            row_cell = xl_rowcol_to_cell(top_row, 0)
            col_cell = xl_rowcol_to_cell(0, left_col)

            self.selections.append(["topRight", col_cell, col_cell])
            self.selections.append(["bottomLeft", row_cell, row_cell])
            self.selections.append(["bottomRight", active_cell, sqref])

        elif col:
            active_pane = "topRight"
            self.selections.append(["topRight", active_cell, sqref])

        else:
            active_pane = "bottomLeft"
            self.selections.append(["bottomLeft", active_cell, sqref])

        # Format splits to the same precision as Excel.
        if x_split:
            attributes.append(("xSplit", "%.16g" % x_split))

        if y_split:
            attributes.append(("ySplit", "%.16g" % y_split))

        attributes.append(("topLeftCell", top_left_cell))

        if has_selection:
            attributes.append(("activePane", active_pane))

        self._xml_empty_tag("pane", attributes)

    def _calculate_x_split_width(self, width):
        # Convert column width from user units to pane split width.

        max_digit_width = 7  # For Calabri 11.
        padding = 5

        # Convert to pixels.
        if width < 1:
            pixels = int(width * (max_digit_width + padding) + 0.5)
        else:
            pixels = int(width * max_digit_width + 0.5) + padding

        # Convert to points.
        points = pixels * 3 / 4

        # Convert to twips (twentieths of a point).
        twips = points * 20

        # Add offset/padding.
        width = twips + 390

        return width

    def _write_table_parts(self):
        # Write the <tableParts> element.
        tables = self.tables
        count = len(tables)

        # Return if worksheet doesn't contain any tables.
        if not count:
            return

        attributes = [
            (
                "count",
                count,
            )
        ]

        self._xml_start_tag("tableParts", attributes)

        for _ in tables:
            # Write the tablePart element.
            self.rel_count += 1
            self._write_table_part(self.rel_count)

        self._xml_end_tag("tableParts")

    def _write_table_part(self, r_id):
        # Write the <tablePart> element.

        r_id = "rId" + str(r_id)

        attributes = [
            (
                "r:id",
                r_id,
            )
        ]

        self._xml_empty_tag("tablePart", attributes)

    def _write_ext_list(self):
        # Write the <extLst> element for data bars and sparklines.
        has_data_bars = len(self.data_bars_2010)
        has_sparklines = len(self.sparklines)

        if not has_data_bars and not has_sparklines:
            return

        # Write the extLst element.
        self._xml_start_tag("extLst")

        if has_data_bars:
            self._write_ext_list_data_bars()

        if has_sparklines:
            self._write_ext_list_sparklines()

        self._xml_end_tag("extLst")

    def _write_ext_list_data_bars(self):
        # Write the Excel 2010 data_bar subelements.
        self._write_ext("{78C0D931-6437-407d-A8EE-F0AAD7539E65}")

        self._xml_start_tag("x14:conditionalFormattings")

        # Write the Excel 2010 conditional formatting data bar elements.
        for data_bar in self.data_bars_2010:
            # Write the x14:conditionalFormatting element.
            self._write_conditional_formatting_2010(data_bar)

        self._xml_end_tag("x14:conditionalFormattings")
        self._xml_end_tag("ext")

    def _write_conditional_formatting_2010(self, data_bar):
        # Write the <x14:conditionalFormatting> element.
        xmlns_xm = "http://schemas.microsoft.com/office/excel/2006/main"

        attributes = [("xmlns:xm", xmlns_xm)]

        self._xml_start_tag("x14:conditionalFormatting", attributes)

        # Write the x14:cfRule element.
        self._write_x14_cf_rule(data_bar)

        # Write the x14:dataBar element.
        self._write_x14_data_bar(data_bar)

        # Write the x14 max and min data bars.
        self._write_x14_cfvo(data_bar["x14_min_type"], data_bar["min_value"])
        self._write_x14_cfvo(data_bar["x14_max_type"], data_bar["max_value"])

        if not data_bar["bar_no_border"]:
            # Write the x14:borderColor element.
            self._write_x14_border_color(data_bar["bar_border_color"])

        # Write the x14:negativeFillColor element.
        if not data_bar["bar_negative_color_same"]:
            self._write_x14_negative_fill_color(data_bar["bar_negative_color"])

        # Write the x14:negativeBorderColor element.
        if (
            not data_bar["bar_no_border"]
            and not data_bar["bar_negative_border_color_same"]
        ):
            self._write_x14_negative_border_color(data_bar["bar_negative_border_color"])

        # Write the x14:axisColor element.
        if data_bar["bar_axis_position"] != "none":
            self._write_x14_axis_color(data_bar["bar_axis_color"])

        self._xml_end_tag("x14:dataBar")
        self._xml_end_tag("x14:cfRule")

        # Write the xm:sqref element.
        self._xml_data_element("xm:sqref", data_bar["range"])

        self._xml_end_tag("x14:conditionalFormatting")

    def _write_x14_cf_rule(self, data_bar):
        # Write the <x14:cfRule> element.
        rule_type = "dataBar"
        guid = data_bar["guid"]
        attributes = [("type", rule_type), ("id", guid)]

        self._xml_start_tag("x14:cfRule", attributes)

    def _write_x14_data_bar(self, data_bar):
        # Write the <x14:dataBar> element.
        min_length = 0
        max_length = 100

        attributes = [
            ("minLength", min_length),
            ("maxLength", max_length),
        ]

        if not data_bar["bar_no_border"]:
            attributes.append(("border", 1))

        if data_bar["bar_solid"]:
            attributes.append(("gradient", 0))

        if data_bar["bar_direction"] == "left":
            attributes.append(("direction", "leftToRight"))

        if data_bar["bar_direction"] == "right":
            attributes.append(("direction", "rightToLeft"))

        if data_bar["bar_negative_color_same"]:
            attributes.append(("negativeBarColorSameAsPositive", 1))

        if (
            not data_bar["bar_no_border"]
            and not data_bar["bar_negative_border_color_same"]
        ):
            attributes.append(("negativeBarBorderColorSameAsPositive", 0))

        if data_bar["bar_axis_position"] == "middle":
            attributes.append(("axisPosition", "middle"))

        if data_bar["bar_axis_position"] == "none":
            attributes.append(("axisPosition", "none"))

        self._xml_start_tag("x14:dataBar", attributes)

    def _write_x14_cfvo(self, rule_type, value):
        # Write the <x14:cfvo> element.
        attributes = [("type", rule_type)]

        if rule_type in ("min", "max", "autoMin", "autoMax"):
            self._xml_empty_tag("x14:cfvo", attributes)
        else:
            self._xml_start_tag("x14:cfvo", attributes)
            self._xml_data_element("xm:f", value)
            self._xml_end_tag("x14:cfvo")

    def _write_x14_border_color(self, rgb):
        # Write the <x14:borderColor> element.
        attributes = [("rgb", rgb)]
        self._xml_empty_tag("x14:borderColor", attributes)

    def _write_x14_negative_fill_color(self, rgb):
        # Write the <x14:negativeFillColor> element.
        attributes = [("rgb", rgb)]
        self._xml_empty_tag("x14:negativeFillColor", attributes)

    def _write_x14_negative_border_color(self, rgb):
        # Write the <x14:negativeBorderColor> element.
        attributes = [("rgb", rgb)]
        self._xml_empty_tag("x14:negativeBorderColor", attributes)

    def _write_x14_axis_color(self, rgb):
        # Write the <x14:axisColor> element.
        attributes = [("rgb", rgb)]
        self._xml_empty_tag("x14:axisColor", attributes)

    def _write_ext_list_sparklines(self):
        # Write the sparkline extension sub-elements.
        self._write_ext("{05C60535-1F16-4fd2-B633-F4F36F0B64E0}")

        # Write the x14:sparklineGroups element.
        self._write_sparkline_groups()

        # Write the sparkline elements.
        for sparkline in reversed(self.sparklines):
            # Write the x14:sparklineGroup element.
            self._write_sparkline_group(sparkline)

            # Write the x14:colorSeries element.
            self._write_color_series(sparkline["series_color"])

            # Write the x14:colorNegative element.
            self._write_color_negative(sparkline["negative_color"])

            # Write the x14:colorAxis element.
            self._write_color_axis()

            # Write the x14:colorMarkers element.
            self._write_color_markers(sparkline["markers_color"])

            # Write the x14:colorFirst element.
            self._write_color_first(sparkline["first_color"])

            # Write the x14:colorLast element.
            self._write_color_last(sparkline["last_color"])

            # Write the x14:colorHigh element.
            self._write_color_high(sparkline["high_color"])

            # Write the x14:colorLow element.
            self._write_color_low(sparkline["low_color"])

            if sparkline["date_axis"]:
                self._xml_data_element("xm:f", sparkline["date_axis"])

            self._write_sparklines(sparkline)

            self._xml_end_tag("x14:sparklineGroup")

        self._xml_end_tag("x14:sparklineGroups")
        self._xml_end_tag("ext")

    def _write_sparklines(self, sparkline):
        # Write the <x14:sparklines> element and <x14:sparkline> sub-elements.

        # Write the sparkline elements.
        self._xml_start_tag("x14:sparklines")

        for i in range(sparkline["count"]):
            spark_range = sparkline["ranges"][i]
            location = sparkline["locations"][i]

            self._xml_start_tag("x14:sparkline")
            self._xml_data_element("xm:f", spark_range)
            self._xml_data_element("xm:sqref", location)
            self._xml_end_tag("x14:sparkline")

        self._xml_end_tag("x14:sparklines")

    def _write_ext(self, uri):
        # Write the <ext> element.
        schema = "http://schemas.microsoft.com/office/"
        xmlns_x14 = schema + "spreadsheetml/2009/9/main"

        attributes = [
            ("xmlns:x14", xmlns_x14),
            ("uri", uri),
        ]

        self._xml_start_tag("ext", attributes)

    def _write_sparkline_groups(self):
        # Write the <x14:sparklineGroups> element.
        xmlns_xm = "http://schemas.microsoft.com/office/excel/2006/main"

        attributes = [("xmlns:xm", xmlns_xm)]

        self._xml_start_tag("x14:sparklineGroups", attributes)

    def _write_sparkline_group(self, options):
        # Write the <x14:sparklineGroup> element.
        #
        # Example for order.
        #
        # <x14:sparklineGroup
        #     manualMax="0"
        #     manualMin="0"
        #     lineWeight="2.25"
        #     type="column"
        #     dateAxis="1"
        #     displayEmptyCellsAs="span"
        #     markers="1"
        #     high="1"
        #     low="1"
        #     first="1"
        #     last="1"
        #     negative="1"
        #     displayXAxis="1"
        #     displayHidden="1"
        #     minAxisType="custom"
        #     maxAxisType="custom"
        #     rightToLeft="1">
        #
        empty = options.get("empty")
        attributes = []

        if options.get("max") is not None:
            if options["max"] == "group":
                options["cust_max"] = "group"
            else:
                attributes.append(("manualMax", options["max"]))
                options["cust_max"] = "custom"

        if options.get("min") is not None:
            if options["min"] == "group":
                options["cust_min"] = "group"
            else:
                attributes.append(("manualMin", options["min"]))
                options["cust_min"] = "custom"

        # Ignore the default type attribute (line).
        if options["type"] != "line":
            attributes.append(("type", options["type"]))

        if options.get("weight"):
            attributes.append(("lineWeight", options["weight"]))

        if options.get("date_axis"):
            attributes.append(("dateAxis", 1))

        if empty:
            attributes.append(("displayEmptyCellsAs", empty))

        if options.get("markers"):
            attributes.append(("markers", 1))

        if options.get("high"):
            attributes.append(("high", 1))

        if options.get("low"):
            attributes.append(("low", 1))

        if options.get("first"):
            attributes.append(("first", 1))

        if options.get("last"):
            attributes.append(("last", 1))

        if options.get("negative"):
            attributes.append(("negative", 1))

        if options.get("axis"):
            attributes.append(("displayXAxis", 1))

        if options.get("hidden"):
            attributes.append(("displayHidden", 1))

        if options.get("cust_min"):
            attributes.append(("minAxisType", options["cust_min"]))

        if options.get("cust_max"):
            attributes.append(("maxAxisType", options["cust_max"]))

        if options.get("reverse"):
            attributes.append(("rightToLeft", 1))

        self._xml_start_tag("x14:sparklineGroup", attributes)

    def _write_spark_color(self, element, color):
        # Helper function for the sparkline color functions below.
        attributes = []

        if color.get("rgb"):
            attributes.append(("rgb", color["rgb"]))

        if color.get("theme"):
            attributes.append(("theme", color["theme"]))

        if color.get("tint"):
            attributes.append(("tint", color["tint"]))

        self._xml_empty_tag(element, attributes)

    def _write_color_series(self, color):
        # Write the <x14:colorSeries> element.
        self._write_spark_color("x14:colorSeries", color)

    def _write_color_negative(self, color):
        # Write the <x14:colorNegative> element.
        self._write_spark_color("x14:colorNegative", color)

    def _write_color_axis(self):
        # Write the <x14:colorAxis> element.
        self._write_spark_color("x14:colorAxis", {"rgb": "FF000000"})

    def _write_color_markers(self, color):
        # Write the <x14:colorMarkers> element.
        self._write_spark_color("x14:colorMarkers", color)

    def _write_color_first(self, color):
        # Write the <x14:colorFirst> element.
        self._write_spark_color("x14:colorFirst", color)

    def _write_color_last(self, color):
        # Write the <x14:colorLast> element.
        self._write_spark_color("x14:colorLast", color)

    def _write_color_high(self, color):
        # Write the <x14:colorHigh> element.
        self._write_spark_color("x14:colorHigh", color)

    def _write_color_low(self, color):
        # Write the <x14:colorLow> element.
        self._write_spark_color("x14:colorLow", color)

    def _write_phonetic_pr(self):
        # Write the <phoneticPr> element.
        attributes = [
            ("fontId", "0"),
            ("type", "noConversion"),
        ]

        self._xml_empty_tag("phoneticPr", attributes)

    def _write_ignored_errors(self):
        # Write the <ignoredErrors> element.
        if not self.ignored_errors:
            return

        self._xml_start_tag("ignoredErrors")

        if self.ignored_errors.get("number_stored_as_text"):
            ignored_range = self.ignored_errors["number_stored_as_text"]
            self._write_ignored_error("numberStoredAsText", ignored_range)

        if self.ignored_errors.get("eval_error"):
            ignored_range = self.ignored_errors["eval_error"]
            self._write_ignored_error("evalError", ignored_range)

        if self.ignored_errors.get("formula_differs"):
            ignored_range = self.ignored_errors["formula_differs"]
            self._write_ignored_error("formula", ignored_range)

        if self.ignored_errors.get("formula_ignored_range"):
            ignored_range = self.ignored_errors["formula_ignored_range"]
            self._write_ignored_error("formulaIgnored_range", ignored_range)

        if self.ignored_errors.get("formula_unlocked"):
            ignored_range = self.ignored_errors["formula_unlocked"]
            self._write_ignored_error("unlockedFormula", ignored_range)

        if self.ignored_errors.get("empty_cell_reference"):
            ignored_range = self.ignored_errors["empty_cell_reference"]
            self._write_ignored_error("emptyCellReference", ignored_range)

        if self.ignored_errors.get("list_data_validation"):
            ignored_range = self.ignored_errors["list_data_validation"]
            self._write_ignored_error("listDataValidation", ignored_range)

        if self.ignored_errors.get("calculated_column"):
            ignored_range = self.ignored_errors["calculated_column"]
            self._write_ignored_error("calculatedColumn", ignored_range)

        if self.ignored_errors.get("two_digit_text_year"):
            ignored_range = self.ignored_errors["two_digit_text_year"]
            self._write_ignored_error("twoDigitTextYear", ignored_range)

        self._xml_end_tag("ignoredErrors")

    def _write_ignored_error(self, type, ignored_range):
        # Write the <ignoredError> element.
        attributes = [
            ("sqref", ignored_range),
            (type, 1),
        ]

        self._xml_empty_tag("ignoredError", attributes)
