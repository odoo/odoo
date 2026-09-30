# -*- coding: utf-8 -*-
#pylint: disable=deprecated-module
import csv
import codecs
import io
import typing
import warnings

_reader = codecs.getreader('utf-8')
_writer = codecs.getwriter('utf-8')


def csv_reader(stream, **params):
    warnings.warn("Deprecated since Odoo 18.0: can just use `csv.reader` with a text stream or use `TextIOWriter` or `codec.getreader` to transcode.", DeprecationWarning, stacklevel=2)
    assert not isinstance(stream, io.TextIOBase),\
        "For cross-compatibility purposes, csv_reader takes a bytes stream"
    return csv.reader(_reader(stream), **params)


def csv_writer(stream, **params):
    warnings.warn("Deprecated since Odoo 18.0: can just use `csv.writer` with a text stream or use `TextIOWriter` or `codec.getwriter` to transcode.", DeprecationWarning, stacklevel=2)
    assert not isinstance(stream, io.TextIOBase), \
        "For cross-compatibility purposes, csv_writer takes a bytes stream"
    return csv.writer(_writer(stream), **params)


def to_text(source: typing.Any) -> str:
    """ Generates a text value from an arbitrary source.

    * False and None are converted to empty strings
    * text is passed through
    * bytes are decoded as UTF-8
    * rest is textified
    """
    warnings.warn("Deprecated since Odoo 18.0.", DeprecationWarning, stacklevel=2)
    if source is None or source is False:
        return ''

    if isinstance(source, bytes):
        return source.decode()

    if isinstance(source, str):
        return source

    return str(source)
