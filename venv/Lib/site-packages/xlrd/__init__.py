# Copyright (c) 2005-2012 Stephen John Machin, Lingfo Pty Ltd
# This module is part of the xlrd package, which is released under a
# BSD-style licence.
import os
import pprint
import sys
import zipfile

from . import timemachine
from .biffh import (
    XL_CELL_BLANK, XL_CELL_BOOLEAN, XL_CELL_DATE, XL_CELL_EMPTY, XL_CELL_ERROR,
    XL_CELL_NUMBER, XL_CELL_TEXT, XLRDError, biff_text_from_num,
    error_text_from_code,
)
from .book import Book, colname, open_workbook_xls
from .compdoc import SIGNATURE as XLS_SIGNATURE
from .formula import *  # is constrained by __all__
from .info import __VERSION__, __version__
from .sheet import empty_cell
from .xldate import XLDateError, xldate_as_datetime, xldate_as_tuple


#: descriptions of the file types :mod:`xlrd` can :func:`inspect <inspect_format>`.
FILE_FORMAT_DESCRIPTIONS = {
    'xls': 'Excel xls',
    'xlsb': 'Excel 2007 xlsb file',
    'xlsx': 'Excel xlsx file',
    'ods': 'Openoffice.org ODS file',
    'zip': 'Unknown ZIP file',
    None: 'Unknown file type',
}

ZIP_SIGNATURE = b"PK\x03\x04"

PEEK_SIZE = max(len(XLS_SIGNATURE), len(ZIP_SIGNATURE))


def inspect_format(path=None, content=None):
    """
    Inspect the content at the supplied path or the :class:`bytes` content provided
    and return the file's type as a :class:`str`, or ``None`` if it cannot
    be determined.

    :param path:
      A :class:`string <str>` path containing the content to inspect.
      ``~`` will be expanded.

    :param content:
      The :class:`bytes` content to inspect.

    :returns:
       A :class:`str`, or ``None`` if the format cannot be determined.
       The return value can always be looked up in :data:`FILE_FORMAT_DESCRIPTIONS`
       to return a human-readable description of the format found.
    """
    if content:
        peek = content[:PEEK_SIZE]
    else:
        path = os.path.expanduser(path)
        with open(path, "rb") as f:
            peek = f.read(PEEK_SIZE)

    if peek.startswith(XLS_SIGNATURE):
        return 'xls'

    if peek.startswith(ZIP_SIGNATURE):
        zf = zipfile.ZipFile(timemachine.BYTES_IO(content) if content else path)

        # Workaround for some third party files that use forward slashes and
        # lower case names. We map the expected name in lowercase to the
        # actual filename in the zip container.
        component_names = {name.replace('\\', '/').lower(): name
                           for name in zf.namelist()}

        if 'xl/workbook.xml' in component_names:
            return 'xlsx'
        if 'xl/workbook.bin' in component_names:
            return 'xlsb'
        if 'content.xml' in component_names:
            return 'ods'
        return 'zip'


def open_workbook(filename=None,
                  logfile=sys.stdout,
                  verbosity=0,
                  use_mmap=True,
                  file_contents=None,
                  encoding_override=None,
                  formatting_info=False,
                  on_demand=False,
                  ragged_rows=False,
                  ignore_workbook_corruption=False
                  ):
    """
    Open a spreadsheet file for data extraction.

    :param filename: The path to the spreadsheet file to be opened.

    :param logfile: An open file to which messages and diagnostics are written.

    :param verbosity: Increases the volume of trace material written to the
                      logfile.

    :param use_mmap:

      Whether to use the mmap module is determined heuristically.
      Use this arg to override the result.

      Current heuristic: mmap is used if it exists.

    :param file_contents:

      A string or an :class:`mmap.mmap` object or some other behave-alike
      object. If ``file_contents`` is supplied, ``filename`` will not be used,
      except (possibly) in messages.

    :param encoding_override:

      Used to overcome missing or bad codepage information
      in older-version files. See :doc:`unicode`.

    :param formatting_info:

      The default is ``False``, which saves memory.
      In this case, "Blank" cells, which are those with their own formatting
      information but no data, are treated as empty by ignoring the file's
      ``BLANK`` and ``MULBLANK`` records.
      This cuts off any bottom or right "margin" of rows of empty or blank
      cells.
      Only :meth:`~xlrd.sheet.Sheet.cell_value` and
      :meth:`~xlrd.sheet.Sheet.cell_type` are available.

      When ``True``, formatting information will be read from the spreadsheet
      file. This provides all cells, including empty and blank cells.
      Formatting information is available for each cell.

      Note that this will raise a NotImplementedError when used with an
      xlsx file.

    :param on_demand:

      Governs whether sheets are all loaded initially or when demanded
      by the caller. See :doc:`on_demand`.

    :param ragged_rows:

      The default of ``False`` means all rows are padded out with empty cells so
      that all rows have the same size as found in
      :attr:`~xlrd.sheet.Sheet.ncols`.

      ``True`` means that there are no empty cells at the ends of rows.
      This can result in substantial memory savings if rows are of widely
      varying sizes. See also the :meth:`~xlrd.sheet.Sheet.row_len` method.


    :param ignore_workbook_corruption:

      This option allows to read corrupted workbooks.
      When ``False`` you may face CompDocError: Workbook corruption.
      When ``True`` that exception will be ignored.

    :returns: An instance of the :class:`~xlrd.book.Book` class.
    """

    file_format = inspect_format(filename, file_contents)
    # We have to let unknown file formats pass through here, as some ancient
    # files that xlrd can parse don't start with the expected signature.
    if file_format and file_format != 'xls':
        raise XLRDError(FILE_FORMAT_DESCRIPTIONS[file_format]+'; not supported')

    bk = open_workbook_xls(
        filename=filename,
        logfile=logfile,
        verbosity=verbosity,
        use_mmap=use_mmap,
        file_contents=file_contents,
        encoding_override=encoding_override,
        formatting_info=formatting_info,
        on_demand=on_demand,
        ragged_rows=ragged_rows,
        ignore_workbook_corruption=ignore_workbook_corruption,
    )

    return bk


def dump(filename, outfile=sys.stdout, unnumbered=False):
    """
    For debugging: dump an XLS file's BIFF records in char & hex.

    :param filename: The path to the file to be dumped.
    :param outfile: An open file, to which the dump is written.
    :param unnumbered: If true, omit offsets (for meaningful diffs).
    """
    from .biffh import biff_dump
    bk = Book()
    bk.biff2_8_load(filename=filename, logfile=outfile, )
    biff_dump(bk.mem, bk.base, bk.stream_len, 0, outfile, unnumbered)


def count_records(filename, outfile=sys.stdout):
    """
    For debugging and analysis: summarise the file's BIFF records.
    ie: produce a sorted file of ``(record_name, count)``.

    :param filename: The path to the file to be summarised.
    :param outfile: An open file, to which the summary is written.
    """
    from .biffh import biff_count_records
    bk = Book()
    bk.biff2_8_load(filename=filename, logfile=outfile, )
    biff_count_records(bk.mem, bk.base, bk.stream_len, outfile)
