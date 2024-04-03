# -*- coding: utf-8 -*-
'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os
import sys
import gevent

from optparse import OptionParser

sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from common import dump
from ebaysdk.finding import Connection as finding
from ebaysdk.http import Connection as html
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

    timeout = gevent.Timeout(4)
    timeout.start()

    try:
        calls = []

        for page in range(1, 10):
            api = finding(debug=opts.debug, appid=opts.appid,
                          config_file=opts.yaml)
            call = gevent.spawn(api.execute,
                                'findItemsAdvanced',
                                {'keywords': 'python',
                                 'paginationInput': {'pageNumber': page}})
            calls.append(call)

        gevent.joinall(calls)

        try:
            call_results = [c.get() for c in calls]

            toprated = 0
            for resp in call_results:
                for item in resp.reply.searchResult.item:
                    if item.topRatedListing == 'true':
                        toprated += 1

            print("Top Rated Listings: %s" % toprated)

        except ConnectionError as e:
            print("%s" % e)

    except gevent.timeout.Timeout as e:
        print("Calls reached timeout threshold: %s" % e)

    finally:
        timeout.cancel()

if __name__ == "__main__":
    (opts, args) = init_options()
    run(opts)
