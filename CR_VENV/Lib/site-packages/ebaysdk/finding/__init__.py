# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os

from ebaysdk import log
from ebaysdk.connection import BaseConnection
from ebaysdk.exception import RequestPaginationError, PaginationLimit
from ebaysdk.config import Config
from ebaysdk.utils import dict2xml


class Connection(BaseConnection):
    """Connection class for the Finding service

    API documentation:
    https://www.x.com/developers/ebay/products/finding-api

    Supported calls:
    findItemsAdvanced
    findItemsByCategory
    (all others, see API docs)

    Doctests:
    >>> f = Connection(config_file=os.environ.get('EBAY_YAML'), debug=False)
    >>> retval = f.execute('findItemsAdvanced', {'keywords': u'niño'})
    >>> error = f.error()
    >>> print(error)
    None
    >>> if not f.error():
    ...   print(f.response.reply.itemSearchURL != '')
    ...   items = f.response.reply.searchResult.item
    ...   print(len(items) > 2)
    ...   print(f.response.reply.ack)
    True
    True
    Success

    """

    def __init__(self, **kwargs):
        """Finding class constructor.

        Keyword arguments:
        domain        -- API endpoint (default: svcs.ebay.com)
        config_file   -- YAML defaults (default: ebay.yaml)
        debug         -- debugging enabled (default: False)
        warnings      -- warnings enabled (default: False)
        uri           -- API endpoint uri (default: /services/search/FindingService/v1)
        appid         -- eBay application id
        siteid        -- eBay country site id (default: EBAY-US)
        version       -- version number (default: 1.0.0)
        https         -- execute of https (default: False)
        proxy_host    -- proxy hostname
        proxy_port    -- proxy port number
        timeout       -- HTTP request timeout (default: 20)
        parallel      -- ebaysdk parallel object
        response_encoding -- API encoding (default: XML)
        request_encoding  -- API encoding (default: XML)
        """

        super(Connection, self).__init__(method='POST', **kwargs)

        self.config = Config(domain=kwargs.get('domain', 'svcs.ebay.com'),
                             connection_kwargs=kwargs,
                             config_file=kwargs.get('config_file', 'ebay.yaml'))

        # override yaml defaults with args sent to the constructor
        self.config.set('domain', kwargs.get('domain', 'svcs.ebay.com'))
        self.config.set('uri', '/services/search/FindingService/v1')
        self.config.set('https', False)
        self.config.set('warnings', True)
        self.config.set('errors', True)
        self.config.set('siteid', 'EBAY-US')
        self.config.set('response_encoding', 'XML')
        self.config.set('request_encoding', 'XML')
        self.config.set('proxy_host', None)
        self.config.set('proxy_port', None)
        self.config.set('token', None)
        self.config.set('iaf_token', None)
        self.config.set('appid', None)
        self.config.set('version', '1.12.0')
        self.config.set('service', 'FindingService')
        self.config.set(
            'doc_url', 'http://developer.ebay.com/DevZone/finding/CallRef/index.html')

        self.datetime_nodes = ['starttimefrom', 'timestamp', 'starttime',
                               'endtime']
        self.base_list_nodes = [
            'findcompleteditemsresponse.categoryhistogramcontainer.categoryhistogram',
            'finditemsadvancedresponse.categoryhistogramcontainer.categoryhistogram',
            'finditemsbycategoryresponse.categoryhistogramcontainer.categoryhistogram',
            'finditemsbyimageresponse.categoryhistogramcontainer.categoryhistogram',
            'finditemsbykeywordsresponse.categoryhistogramcontainer.categoryhistogram',
            'finditemsbyproductresponse.categoryhistogramcontainer.categoryhistogram',
            'finditemsinebaystoresresponse.categoryhistogramcontainer.categoryhistogram',
            'findcompleteditemsresponse.aspecthistogramcontainer.aspect',
            'finditemsadvancedresponse.aspecthistogramcontainer.aspect',
            'finditemsbycategoryresponse.aspecthistogramcontainer.aspect',
            'finditemsbyimageresponse.aspecthistogramcontainer.aspect',
            'finditemsbykeywordsresponse.aspecthistogramcontainer.aspect',
            'finditemsbyproductresponse.aspecthistogramcontainer.aspect',
            'finditemsinebaystoresresponse.aspecthistogramcontainer.aspect',
            'findcompleteditemsresponse.aspect.valuehistogram',
            'finditemsadvancedresponse.aspect.valuehistogram',
            'finditemsbycategoryresponse.aspect.valuehistogram',
            'finditemsbyimageresponse.aspect.valuehistogram',
            'finditemsbykeywordsresponse.aspect.valuehistogram',
            'finditemsbyproductresponse.aspect.valuehistogram',
            'finditemsinebaystoresresponse.aspect.valuehistogram',
            'findcompleteditemsresponse.aspectfilter.aspectvaluename',
            'finditemsadvancedresponse.aspectfilter.aspectvaluename',
            'finditemsbycategoryresponse.aspectfilter.aspectvaluename',
            'finditemsbyimageresponse.aspectfilter.aspectvaluename',
            'finditemsbykeywordsresponse.aspectfilter.aspectvaluename',
            'finditemsbyproductresponse.aspectfilter.aspectvaluename',
            'finditemsinebaystoresresponse.aspectfilter.aspectvaluename',
            'findcompleteditemsresponse.searchresult.item',
            'finditemsadvancedresponse.searchresult.item',
            'finditemsbycategoryresponse.searchresult.item',
            'finditemsbyimageresponse.searchresult.item',
            'finditemsbykeywordsresponse.searchresult.item',
            'finditemsbyproductresponse.searchresult.item',
            'finditemsinebaystoresresponse.searchresult.item',
            'findcompleteditemsresponse.domainfilter.domainname',
            'finditemsadvancedresponse.domainfilter.domainname',
            'finditemsbycategoryresponse.domainfilter.domainname',
            'finditemsbyimageresponse.domainfilter.domainname',
            'finditemsbykeywordsresponse.domainfilter.domainname',
            'finditemsinebaystoresresponse.domainfilter.domainname',
            'findcompleteditemsresponse.itemfilter.value',
            'finditemsadvancedresponse.itemfilter.value',
            'finditemsbycategoryresponse.itemfilter.value',
            'finditemsbyimageresponse.itemfilter.value',
            'finditemsbykeywordsresponse.itemfilter.value',
            'finditemsbyproductresponse.itemfilter.value',
            'finditemsinebaystoresresponse.itemfilter.value',
            'findcompleteditemsresponse.conditionhistogramcontainer.conditionhistogram',
            'finditemsadvancedresponse.conditionhistogramcontainer.conditionhistogram',
            'finditemsbycategoryresponse.conditionhistogramcontainer.conditionhistogram',
            'finditemsbyimageresponse.conditionhistogramcontainer.conditionhistogram',
            'finditemsbykeywordsresponse.conditionhistogramcontainer.conditionhistogram',
            'finditemsinebaystoresresponse.conditionhistogramcontainer.conditionhistogram',
            'finditemsbyproductresponse.conditionhistogramcontainer.conditionhistogram',
            'findcompleteditemsresponse.searchitem.paymentmethod',
            'finditemsadvancedresponse.searchitem.paymentmethod',
            'finditemsbycategoryresponse.searchitem.paymentmethod',
            'finditemsbyimageresponse.searchitem.paymentmethod',
            'finditemsbykeywordsresponse.searchitem.paymentmethod',
            'finditemsbyproductresponse.searchitem.paymentmethod',
            'finditemsinebaystoresresponse.searchitem.paymentmethod',
            'findcompleteditemsresponse.searchitem.gallerypluspictureurl',
            'finditemsadvancedresponse.searchitem.gallerypluspictureurl',
            'finditemsbycategoryresponse.searchitem.gallerypluspictureurl',
            'finditemsbyimageresponse.searchitem.gallerypluspictureurl',
            'finditemsbykeywordsresponse.searchitem.gallerypluspictureurl',
            'finditemsbyproductresponse.searchitem.gallerypluspictureurl',
            'finditemsinebaystoresresponse.searchitem.gallerypluspictureurl',
            'finditemsbycategoryresponse.searchitem.attribute',
            'finditemsadvancedresponse.searchitem.attribute',
            'finditemsbykeywordsresponse.searchitem.attribute',
            'finditemsinebaystoresresponse.searchitem.attribute',
            'finditemsbyproductresponse.searchitem.attribute',
            'findcompleteditemsresponse.searchitem.attribute',
            'findcompleteditemsresponse.shippinginfo.shiptolocations',
            'finditemsadvancedresponse.shippinginfo.shiptolocations',
            'finditemsbycategoryresponse.shippinginfo.shiptolocations',
            'finditemsbyimageresponse.shippinginfo.shiptolocations',
            'finditemsbykeywordsresponse.shippinginfo.shiptolocations',
            'finditemsbyproductresponse.shippinginfo.shiptolocations',
            'finditemsinebaystoresresponse.shippinginfo.shiptolocations',
        ]

    def build_request_headers(self, verb):
        return {
            "X-EBAY-SOA-SERVICE-NAME": self.config.get('service', ''),
            "X-EBAY-SOA-SERVICE-VERSION": self.config.get('version', ''),
            "X-EBAY-SOA-SECURITY-APPNAME": self.config.get('appid', ''),
            "X-EBAY-SOA-GLOBAL-ID": self.config.get('siteid', ''),
            "X-EBAY-SOA-OPERATION-NAME": verb,
            "X-EBAY-SOA-REQUEST-DATA-FORMAT": self.config.get('request_encoding', ''),
            "X-EBAY-SOA-RESPONSE-DATA-FORMAT": self.config.get('response_encoding', ''),
            "Content-Type": "text/xml"
        }

    def build_request_data(self, verb, data, verb_attrs):
        xml = "<?xml version='1.0' encoding='utf-8'?>"
        xml += "<" + verb + "Request xmlns=\"http://www.ebay.com/marketplace/search/v1/services\">"
        xml += dict2xml(data, self.escape_xml)
        xml += "</" + verb + "Request>"

        return xml

    def warnings(self):
        warning_string = ""

        if len(self._resp_body_warnings) > 0:
            warning_string = "%s: %s" \
                % (self.verb, ", ".join(self._resp_body_warnings))

        return warning_string

    def _get_resp_body_errors(self):
        """Parses the response content to pull errors.

        Child classes should override this method based on what the errors in the
        XML response body look like. They can choose to look at the 'ack',
        'Errors', 'errorMessage' or whatever other fields the service returns.
        the implementation below is the original code that was part of error()
        """

        if self._resp_body_errors and len(self._resp_body_errors) > 0:
            return self._resp_body_errors

        errors = []
        warnings = []
        resp_codes = []

        if self.verb is None:
            return errors

        dom = self.response.dom()
        if dom is None:
            return errors

        for e in dom.findall("error"):
            eSeverity = None
            eDomain = None
            eMsg = None
            eId = None

            try:
                eSeverity = e.findall('severity')[0].text
            except IndexError:
                pass

            try:
                eDomain = e.findall('domain')[0].text
            except IndexError:
                pass

            try:
                eId = e.findall('errorId')[0].text
                if int(eId) not in resp_codes:
                    resp_codes.append(int(eId))
            except IndexError:
                pass

            try:
                eMsg = e.findall('message')[0].text
            except IndexError:
                pass

            msg = "Domain: %s, Severity: %s, errorId: %s, %s" \
                % (eDomain, eSeverity, eId, eMsg)

            if eSeverity == 'Warning':
                warnings.append(msg)
            else:
                errors.append(msg)

        self._resp_body_warnings = warnings
        self._resp_body_errors = errors
        self._resp_codes = resp_codes

        if self.config.get('warnings') and len(warnings) > 0:
            log.warn("%s: %s\n\n" % (self.verb, "\n".join(warnings)))

        try:
            if self.response.reply.ack == 'Success' and len(errors) > 0 and self.config.get('errors'):
                log.error("%s: %s\n\n" % (self.verb, "\n".join(errors)))

            elif len(errors) > 0:
                if self.config.get('errors'):
                    log.error("%s: %s\n\n" % (self.verb, "\n".join(errors)))

                return errors
        except AttributeError as e:
            return errors

        return []

    def next_page(self):
        if type(self._request_dict) is not dict:
            raise RequestPaginationError(
                "request data is not of type dict", self.response)

        epp = self._request_dict.get(
            'paginationInput', {}).get('enteriesPerPage', None)
        num = int(self.response.reply.paginationOutput.pageNumber)

        if num >= int(self.response.reply.paginationOutput.totalPages):
            raise PaginationLimit("no more pages to process", self.response)
            return None

        self._request_dict['paginationInput'] = {}

        if epp:
            self._request_dict['paginationInput']['enteriesPerPage'] = epp

        self._request_dict['paginationInput']['pageNumber'] = int(num) + 1

        return self.execute(self.verb, self._request_dict)
