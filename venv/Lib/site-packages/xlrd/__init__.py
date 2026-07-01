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
from .book import Book, colname
from .formula import *  # is constrained by __all__
from .info import __VERSION__, __version__
from .sheet import empty_cell
from .xldate import XLDateError, xldate_as_datetime, xldate_as_tuple
from .xlsx import X12Book

if sys.version.startswith("IronPython"):
    # print >> sys.stderr, "...importing encodings"
    import encodings

try:
    import mmap
    MMAP_AVAILABLE = 1
except ImportError:
    MMAP_AVAILABLE = 0
USE_MMAP = MMAP_AVAILABLE

def open_workbook(filename=None,
                  logfile=sys.stdout,
                  verbosity=0,
                  use_mmap=USE_MMAP,
                  file_contents=None,
                  encoding_override=None,
                  formatting_info=False,
                  on_demand=False,
                  ragged_rows=False):
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

    :returns: An instance of the :class:`~xlrd.book.Book` class.
    """

    peeksz = 4
    if file_contents:
        peek = file_contents[:peeksz]
    else:
        filename = os.path.expanduser(filename)
        with open(filename, "rb") as f:
            peek = f.read(peeksz)
    if peek == b"PK\x03\x04": # a ZIP file
        if file_contents:
            zf = zipfile.ZipFile(timemachine.BYTES_IO(file_contents))
        else:
            zf = zipfile.ZipFile(filename)

        # Workaround for some third party files that use forward slashes and
        # lower case names. We map the expected name in lowercase to the
        # actual filename in the zip container.
        component_names = dict([(X12Book.convert_filename(name), name)
                                for name in zf.namelist()])

        if verbosity:
            logfile.write('ZIP component_names:\n')
            pprint.pprint(component_names, logfile)
        if 'xl/workbook.xml' in component_names:
            from . import xlsx
            bk = xlsx.open_workbook_2007_xml(
                zf,
                component_names,
                logfile=logfile,
                verbosity=verbosity,
                use_mmap=use_mmap,
                formatting_info=formatting_info,
                on_demand=on_demand,
                ragged_rows=ragged_rows,
            )
            return bk
        if 'xl/workbook.bin' in component_names:
            raise XLRDError('Excel 2007 xlsb file; not supported')
        if 'content.xml' in component_names:
            raise XLRDError('Openoffice.org ODS file; not supported')
        raise XLRDError('ZIP file contents not a known type of workbook')

    from . import book
    bk = book.open_workbook_xls(
        filename=filename,
        logfile=logfile,
        verbosity=verbosity,
        use_mmap=use_mmap,
        file_contents=file_contents,
        encoding_override=encoding_override,
        formatting_info=formatting_info,
        on_demand=on_demand,
        ragged_rows=ragged_rows,
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
