# -*- coding: utf-8 -*-
'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os
import sys
import datetime
from optparse import OptionParser

sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from common import dump

import ebaysdk
from ebaysdk.utils import getNodeText
from ebaysdk.exception import ConnectionError
from ebaysdk.policies import Connection as Policies


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
    parser.add_option("-p", "--devid",
                      dest="devid", default=None,
                      help="Specifies the eBay developer id to use.")
    parser.add_option("-c", "--certid",
                      dest="certid", default=None,
                      help="Specifies the eBay cert id to use.")

    (opts, args) = parser.parse_args()
    return opts, args


def getSellerProfiles(opts):
    try:
        api = Policies(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                       certid=opts.certid, devid=opts.devid)

        api.execute('getSellerProfiles')
        dump(api)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())


def getConsolidationJobStatus(opts):
    try:
        api = Policies(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                       certid=opts.certid, devid=opts.devid)

        api.execute('getConsolidationJobStatus')
        dump(api)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())

if __name__ == "__main__":
    (opts, args) = init_options()

    print("Business Policies API Samples for version %s" %
          ebaysdk.get_version())

    getSellerProfiles(opts)
    getConsolidationJobStatus(opts)
