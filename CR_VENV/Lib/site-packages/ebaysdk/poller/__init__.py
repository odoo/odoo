# -*- coding: utf-8 -*-
'''
© 2012-2015 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''
import os
import sys
import logging

from contextlib import contextmanager
from optparse import OptionParser
from ebaysdk import log, set_stream_logger


@contextmanager
def file_lock(lock_file):
    if os.path.exists(lock_file):
        log.info("skipping run, lock file found (%s)" % lock_file)
        sys.exit(-1)
    else:
        open(lock_file, 'w').write("1")
        try:
            yield
        finally:
            os.remove(lock_file)


def parse_args(usage):

    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Enabled debugging [default: %default]")
    parser.add_option("-H", "--hours",
                      dest="hours", default=12, type='int',
                      help="Specifies the number of hours [default: %default]")
    parser.add_option("-M", "--minutes",
                      dest="minutes", default=0, type='int',
                      help="Specifies the number of minutes [default: %default]")
    parser.add_option("-y", "--yaml",
                      dest="yaml", default='ebay.yaml',
                      help="Specifies the name of the YAML defaults file. [default: %default]")
    parser.add_option("-a", "--appid",
                      dest="appid", default=None,
                      help="Specifies the eBay application id to use.")
    parser.add_option("-p", "--devid",
                      dest="devid", default=None,
                      help="Specifies the eBay developer id to use.")
    parser.add_option("-c", "--certid",
                      dest="certid", default=None,
                      help="Specifies the eBay cert id to use.")
    parser.add_option("-s", "--siteid",
                      dest="siteid", default=None,
                      help="Specifies the eBay site id to use.")
    parser.add_option("-o", "--OrderRole",
                      dest="OrderRole", default='Buyer',
                      help="Specifies which OrderRole value to use. [default: %default]")
    parser.add_option("-O", "--OrderStatus",
                      dest="OrderStatus", default='All',
                      help="Specifies which OrderStatus value to use. [default: %default]")

    (opts, args) = parser.parse_args()

    if opts.debug:
        set_stream_logger(level=logging.DEBUG)

    return opts, args
