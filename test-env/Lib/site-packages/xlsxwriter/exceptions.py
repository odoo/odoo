###############################################################################
#
# Exceptions - A class for XlsxWriter exceptions.
#
# Copyright 2013-2018, John McNamara, jmcnamara@cpan.org
#


class XlsxWriterException(Exception):
    """Base exception for XlsxWriter."""


class XlsxInputError(XlsxWriterException):
    """Base exception for all input data related errors."""


class XlsxFileError(XlsxWriterException):
    """Base exception for all file related errors."""


class EmptyChartSeries(XlsxInputError):
    """Chart must contain at least one data series."""


class DuplicateTableName(XlsxInputError):
    """Worksheet table name already exists."""


class InvalidWorksheetName(XlsxInputError):
    """Worksheet name is too long or contains restricted characters."""


class DuplicateWorksheetName(XlsxInputError):
    """Worksheet name already exists."""


class UndefinedImageSize(XlsxFileError):
    """No size data found in image file."""


class UnsupportedImageFormat(XlsxFileError):
    """Unsupported image file format."""
