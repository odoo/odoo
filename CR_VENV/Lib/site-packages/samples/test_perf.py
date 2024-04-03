# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''
import sys
import os
import ujson
import json

sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from ebaysdk.utils import dict2xml
from ebaysdk.response import Response, ResponseDataObject


def tojson():
    sample_dict = {
        'searchFilter': {'categoryId': {'#text': 222, '@attrs': {'site': 'US'}}},
        'paginationInput': {
            'pageNumber': '1',
            'pageSize': '25'
        },
        'itemFilter': [
            {'name': 'Condition',
             'value': 'Used'},
            {'name': 'LocatedIn',
             'value': 'GB'},
        ],
        'sortOrder': 'StartTimeNewest'
    }

    json.dumps(sample_dict)


def toujson():
    sample_dict = {
        'searchFilter': {'categoryId': {'#text': 222, '@attrs': {'site': 'US'}}},
        'paginationInput': {
            'pageNumber': '1',
            'pageSize': '25'
        },
        'itemFilter': [
            {'name': 'Condition',
             'value': 'Used'},
            {'name': 'LocatedIn',
             'value': 'GB'},
        ],
        'sortOrder': 'StartTimeNewest'
    }

    ujson.dumps(sample_dict)


def response():

    xml = b'<?xml version="1.0" encoding="UTF-8"?><findItemsByProductResponse xmlns="http://www.ebay.com/marketplace/search/v1/services"><ack>Success</ack><version>1.12.0</version><timestamp>2014-02-07T23:31:13.941Z</timestamp><searchResult count="1"><item><name>Item Two</name></item></searchResult><paginationOutput><pageNumber>1</pageNumber><entriesPerPage>1</entriesPerPage><totalPages>90</totalPages><totalEntries>179</totalEntries></paginationOutput><itemSearchURL>http://www.ebay.com/ctg/53039031?_ddo=1&amp;_ipg=2&amp;_pgn=1</itemSearchURL></findItemsByProductResponse>'
    o = ResponseDataObject({'content': xml}, [])
    r = Response(o, verb='findItemsByProduct', list_nodes=[
                 'finditemsbyproductresponse.searchresult.item', 'finditemsbyproductresponse.paginationoutput.pagenumber'])


def main():
    sample_dict = {
        'searchFilter': {'categoryId': {'#text': 222, '@attrs': {'site': 'US'}}},
        'paginationInput': {
            'pageNumber': '1',
            'pageSize': '25'
        },
        'itemFilter': [
            {'name': 'Condition',
             'value': 'Used'},
            {'name': 'LocatedIn',
             'value': 'GB'},
        ],
        'sortOrder': 'StartTimeNewest'
    }

    xml = dict2xml(sample_dict)

if __name__ == '__main__':

    import timeit

    print("To JSON %s" %
          timeit.repeat("tojson()", number=1000, repeat=9,
                        setup="from __main__ import tojson"))

    print("To uJSON %s" %
          timeit.repeat("toujson()", number=1000, repeat=9,
                        setup="from __main__ import toujson"))

    print("dict2xml() %s" %
          timeit.repeat("main()", number=1000, repeat=9,
                        setup="from __main__ import main"))

    print("Response Class %s" %
          timeit.repeat("response()", number=1000, repeat=9,
                        setup="from __main__ import response"))
