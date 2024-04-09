# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os

from ebaysdk.soa import Connection as BaseConnection
from ebaysdk.utils import dict2xml, getNodeText


class Connection(BaseConnection):
    """
    Not to be confused with Finding service

    Implements FindItemServiceNextGen

    https://wiki.vip.corp.ebay.com/display/apdoc/FindItemServiceNextGen

    This class is a bit hackish, it subclasses SOAService, but removes
    SOAP support. FindItemServiceNextGen works fine with standard XML
    and lets avoid all of the ugliness associated with SOAP.

    >>> from ebaysdk.shopping import Connection as Shopping
    >>> s = Shopping(config_file=os.environ.get('EBAY_YAML'))
    >>> retval = s.execute('FindPopularItems', {'QueryKeywords': 'Python'})
    >>> nodes = s.response_dom().getElementsByTagName('ItemID')
    >>> itemIds = [getNodeText(n) for n in nodes]
    >>> len(itemIds) > 0
    True
    >>> f = Connection(debug=False, config_file=os.environ.get('EBAY_YAML'))
    >>> records = f.find_items_by_ids(itemIds)
    >>> len(records) > 0
    True
    """

    def __init__(self, site_id='EBAY-US', debug=False, consumer_id=None,
                 domain='apifindingcore.vip.ebay.com', **kwargs):

        super(Connection, self).__init__(consumer_id=consumer_id,
                                         domain=domain,
                                         app_config=None,
                                         site_id=site_id,
                                         debug=debug, **kwargs)

        self.config.set('domain', 'apifindingcore.vip.ebay.com')
        self.config.set('service', 'FindItemServiceNextGen', force=True)
        self.config.set('https', False)
        self.config.set(
            'uri', "/services/search/FindItemServiceNextGen/v1", force=True)
        self.config.set('consumer_id', consumer_id)

        self.read_set = None

        self.datetime_nodes += ['lastupdatetime', 'timestamp']
        self.base_list_nodes += ['finditemsbyidsresponse.record']

    def build_request_headers(self, verb):
        return {
            "X-EBAY-SOA-SERVICE-NAME": self.config.get('service', ''),
            "X-EBAY-SOA-SERVICE-VERSION": self.config.get('version', ''),
            "X-EBAY-SOA-GLOBAL-ID": self.config.get('siteid', ''),
            "X-EBAY-SOA-OPERATION-NAME": verb,
            "X-EBAY-SOA-CONSUMER-ID": self.config.get('consumer_id', ''),
            "Content-Type": "text/xml"
        }

    def findItemsByIds(self, ebay_item_ids,
                       read_set=['ITEM_ID', 'TITLE', 'SELLER_NAME', 'ALL_CATS', 'ITEM_CONDITION_NEW']):

        self.read_set = read_set
        read_set_node = []

        for rtype in self.read_set:
            read_set_node.append({
                'member': {
                    'namespace': 'ItemDictionary',
                    'name': rtype
                }
            })

        args = {'id': ebay_item_ids, 'readSet': read_set_node}
        self.execute('findItemsByIds', args)
        return self.mappedResponse()

    def mappedResponse(self):
        records = []

        for r in self.response.dict().get('record', []):
            mydict = dict()
            i = 0

            for values_dict in r.get('value', {}):

                if values_dict is None:
                    continue

                for key, value in values_dict.items():
                    value_data = None
                    if type(value) == list:
                        value_data = [x for x in value]
                    else:
                        value_data = value

                    mydict.update({self.read_set[i]: value_data})

                    i = i + 1

            records.append(mydict)

        return records

    def find_items_by_ids(self, *args, **kwargs):
        return self.findItemsByIds(*args, **kwargs)

    def build_request_data(self, verb, data, verb_attrs):
        xml = "<?xml version='1.0' encoding='utf-8'?>"
        xml += "<" + verb + "Request"
        xml += ' xmlns="http://www.ebay.com/marketplace/search/v1/services"'
        xml += '>'
        xml += dict2xml(data, self.escape_xml)
        xml += "</" + verb + "Request>"

        return xml
