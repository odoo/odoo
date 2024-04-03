# -*- coding: utf-8 -*-
'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os
import sys
from optparse import OptionParser

try:
    input = raw_input
except NameError:
    pass

sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from common import dump

import ebaysdk
from ebaysdk.exception import ConnectionError
from ebaysdk.shopping import Connection as Shopping


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
    api = Shopping(debug=opts.debug, appid=opts.appid, config_file=opts.yaml,
                   warnings=True)

    print("Shopping samples for SDK version %s" % ebaysdk.get_version())

    try:
        response = api.execute('FindPopularItems', {'QueryKeywords': 'Python'})

        dump(api)

        print("Matching Titles:")
        for item in response.reply.ItemArray.Item:
            print(item.Title)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())


def popularSearches(opts):

    api = Shopping(debug=opts.debug, appid=opts.appid, config_file=opts.yaml,
                   warnings=True)

    choice = True

    while choice:

        choice = input('Search: ')

        if choice == 'quit':
            break

        mySearch = {
            "MaxKeywords": 10,
            "QueryKeywords": choice,
        }

        try:
            response = api.execute('FindPopularSearches', mySearch)

            dump(api, full=False)

            print("Related: %s" %
                  response.reply.PopularSearchResult.RelatedSearches)

            for term in response.reply.PopularSearchResult.AlternativeSearches.split(';')[:3]:
                api.execute('FindPopularItems', {
                            'QueryKeywords': term, 'MaxEntries': 3})

                print("Term: %s" % term)

                try:
                    for item in response.reply.ItemArray.Item:
                        print(item.Title)
                except AttributeError:
                    pass

                dump(api)

            print("\n")

        except ConnectionError as e:
            print(e)
            print(e.response.dict())


def categoryInfo(opts):

    try:
        api = Shopping(debug=opts.debug, appid=opts.appid, config_file=opts.yaml,
                       warnings=True)

        response = api.execute('GetCategoryInfo', {"CategoryID": 3410})

        dump(api, full=False)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())


def with_affiliate_info(opts):
    try:
        api = Shopping(debug=opts.debug, appid=opts.appid,
                       config_file=opts.yaml, warnings=True,
                       trackingid=1234, trackingpartnercode=9)

        mySearch = {
            "MaxKeywords": 10,
            "QueryKeywords": 'shirt',
        }

        response = api.execute('FindPopularSearches', mySearch)
        dump(api, full=False)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())


def using_attributes(opts):

    try:
        api = Shopping(debug=opts.debug, appid=opts.appid,
                       config_file=opts.yaml, warnings=True)

        response = api.execute('FindProducts', {
            "ProductID": {'@attrs': {'type': 'ISBN'},
                          '#text': '0596154488'}})

        dump(api, full=False)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())

if __name__ == "__main__":
    (opts, args) = init_options()
    run(opts)
    popularSearches(opts)
    categoryInfo(opts)
    with_affiliate_info(opts)
    using_attributes(opts)
