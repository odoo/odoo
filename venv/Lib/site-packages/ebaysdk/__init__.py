# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import platform
import logging

__version__ = '2.1.5'
Version = __version__  # for backward compatibility

try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):

        def emit(self, record):
            pass

UserAgent = 'eBaySDK/%s Python/%s %s/%s' % (
    __version__,
    platform.python_version(),
    platform.system(),
    platform.release()
)

log = logging.getLogger('ebaysdk')

if not log.handlers:
    log.addHandler(NullHandler())


def get_version():
    return __version__


def set_stream_logger(level=logging.DEBUG, format_string=None):
    log.handlers = []

    if not format_string:
        format_string = "%(asctime)s %(name)s [%(levelname)s]:%(message)s"

    log.setLevel(level)
    fh = logging.StreamHandler()
    fh.setLevel(level)
    formatter = logging.Formatter(format_string)
    fh.setFormatter(formatter)
    log.addHandler(fh)


def trading(*args, **kwargs):
    raise ImportError(
        'SDK import must be changed as follows:\n\n- %s\n+ %s\n\n' % (
            'from ebaysdk import trading',
            'from ebaysdk.trading import Connection as trading',
        )
    )


def shopping(*args, **kwargs):
    raise ImportError(
        'SDK import must be changed as follows:\n\n- %s\n+ %s\n\n' % (
            'from ebaysdk import shopping',
            'from ebaysdk.shopping import Connection as shopping',
        )
    )


def finding(*args, **kwargs):
    raise ImportError(
        'SDK import must be changed as follows:\n\n- %s\n+ %s\n\n' % (
            'from ebaysdk import finding',
            'from ebaysdk.finding import Connection as finding',
        )
    )


def merchandising(*args, **kwargs):
    raise ImportError(
        'SDK import must be changed as follows:\n\n- %s\n+ %s\n\n' % (
            'from ebaysdk import merchandising',
            'from ebaysdk.merchandising import Connection as merchandising',
        )
    )


def html(*args, **kwargs):
    raise ImportError(
        'SDK import must be changed as follows:\n\n- %s\n+ %s\n\n' % (
            'from ebaysdk import html',
            'from ebaysdk.http import Connection as html',
        )
    )


def parallel(*args, **kwargs):
    raise ImportError(
        'SDK import must be changed as follows:\n\n- %s\n+ %s\n\n' % (
            'from ebaysdk import parallel',
            'from ebaysdk.parallel import Parallel as parallel',
        )
    )
