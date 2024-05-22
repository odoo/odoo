# -*- coding: utf-8 -*-
#pylint: disable=deprecated-module
import csv
import codecs
import io

_reader = codecs.getreader('utf-8')
_writer = codecs.getwriter('utf-8')


def csv_reader(stream, **params):
    assert not isinstance(stream, io.TextIOBase),\
        "For cross-compatibility purposes, csv_reader takes a bytes stream"
    return csv.reader(_reader(stream), **params)


def csv_writer(stream, **params):
    assert not isinstance(stream, io.TextIOBase), \
        "For cross-compatibility purposes, csv_writer takes a bytes stream"
    return csv.writer(_writer(stream), **params)


def to_text(source):
    """ Generates a text value (an instance of text_type) from an arbitrary
    source.

    * False and None are converted to empty strings
    * text is passed through
    * bytes are decoded as UTF-8
    * rest is textified via the current version's relevant data model method
    """
    if source is None or source is False:
        return u''

    if isinstance(source, bytes):
        return source.decode('utf-8')

    return str(source)
