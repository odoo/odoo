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

from ebaysdk.merchandising import Connection as merchandising
from ebaysdk.exception import ConnectionError


def init_options():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Enabled debugging [default: %default]")
    parser.add_option("-y", "--yaml",
                      dest="yaml", default='ebay.yaml',
                      help="Specifies the name of the YAML defaults file. [default: %default]")
    parser.add_option("-a", "--appid",
                      dest="appid", default=None,
                      help="Specifies the eBay application id to use.")

    (opts, args) = parser.parse_args()
    return opts, args


def run(opts):
    try:
        api = merchandising(debug=opts.debug, appid=opts.appid,
                            config_file=opts.yaml, warnings=True)

        response = api.execute('getMostWatchedItems', {'maxResults': 4})

        dump(api)
    except ConnectionError as e:
        print(e)
        print(e.response.dict())


if __name__ == "__main__":
    (opts, args) = init_options()
    run(opts)
