# -*- coding: utf-8 -*-
'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os
import sys

from optparse import OptionParser

sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from common import dump

import ebaysdk
from ebaysdk.http import Connection as HTTP
from ebaysdk.exception import ConnectionError


def init_options():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Enabled debugging [default: %default]")

    (opts, args) = parser.parse_args()
    return opts, args


def run(opts):

    try:
        api = HTTP(debug=opts.debug, method='GET')

        api.execute('http://feeds.wired.com/wired/index')
        dump(api)

    except ConnectionError as e:
        print(e)

if __name__ == "__main__":
    print("HTTP samples for SDK version %s" % ebaysdk.get_version())
    (opts, args) = init_options()
    run(opts)
