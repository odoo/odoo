# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import inspect
import sys


if sys.version_info < (3,):
    str_cls = unicode  # noqa
    byte_cls = str
    int_types = (int, long)  # noqa

    def bytes_to_list(byte_string):
        return [ord(b) for b in byte_string]

    chr_cls = chr

else:
    str_cls = str
    byte_cls = bytes
    int_types = int

    bytes_to_list = list

    def chr_cls(num):
        return bytes([num])


def type_name(value):
    """
    Returns a user-readable name for the type of an object

    :param value:
        A value to get the type name of

    :return:
        A unicode string of the object's type name
    """

    if inspect.isclass(value):
        cls = value
    else:
        cls = value.__class__
    if cls.__module__ in set(['builtins', '__builtin__']):
        return cls.__name__
    return '%s.%s' % (cls.__module__, cls.__name__)
