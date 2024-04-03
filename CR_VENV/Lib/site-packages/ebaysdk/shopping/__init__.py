# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os

from ebaysdk import log
from ebaysdk.connection import BaseConnection
from ebaysdk.config import Config
from ebaysdk.utils import getNodeText, dict2xml


class Connection(BaseConnection):
    """Shopping API class

    API documentation:
    http://developer.ebay.com/products/shopping/

    Supported calls:
    getSingleItem
    getMultipleItems
    (all others, see API docs)

    Doctests:
    >>> s = Connection(config_file=os.environ.get('EBAY_YAML'))
    >>> retval = s.execute('FindPopularItems', {'QueryKeywords': 'Python'})
    >>> print(s.response_obj().Ack)
    Success
    >>> print(s.error())
    None
    """

    def __init__(self, **kwargs):
        """Shopping class constructor.

        Keyword arguments:
        domain        -- API endpoint (default: open.api.ebay.com)
        config_file   -- YAML defaults (default: ebay.yaml)
        debug         -- debugging enabled (default: False)
        warnings      -- warnings enabled (default: True)
        errors        -- errors enabled (default: True)
        uri           -- API endpoint uri (default: /shopping)
        appid         -- eBay application id
        siteid        -- eBay country site id (default: 0 (US))
        version       -- version number (default: 799)
        https         -- execute of https (default: True)
        proxy_host    -- proxy hostname
        proxy_port    -- proxy port number
        timeout       -- HTTP request timeout (default: 20)
        parallel      -- ebaysdk parallel object
        trackingid    -- ID to identify you to your tracking partner
        trackingpartnercode -- third party who is your tracking partner
        response_encoding   -- API encoding (default: XML)
        request_encoding    -- API encoding (default: XML)

        More affiliate tracking info:
        http://developer.ebay.com/DevZone/shopping/docs/Concepts/ShoppingAPI_FormatOverview.html#StandardURLParameters

        """
        super(Connection, self).__init__(method='POST', **kwargs)

        self.config = Config(domain=kwargs.get('domain', 'open.api.ebay.com'),
                             connection_kwargs=kwargs,
                             config_file=kwargs.get('config_file', 'ebay.yaml'))

        # override yaml defaults with args sent to the constructor
        self.config.set('domain', kwargs.get('domain', 'open.api.ebay.com'))
        self.config.set('uri', '/shopping')
        self.config.set('warnings', True)
        self.config.set('errors', True)
        self.config.set('https', False)
        self.config.set('siteid', '0')
        self.config.set('response_encoding', 'XML')
        self.config.set('request_encoding', 'XML')
        self.config.set('proxy_host', None)
        self.config.set('proxy_port', None)
        self.config.set('appid', None)
        self.config.set('version', '799')
        self.config.set('trackingid', None)
        self.config.set('trackingpartnercode', None)
        self.config.set(
            'doc_url', 'http://developer.ebay.com/DevZone/Shopping/docs/CallRef/index.html')

        if self.config.get('https') and self.debug:
            print("HTTPS is not supported on the Shopping API.")

        self.datetime_nodes = ['timestamp', 'registrationdate', 'creationtime',
                               'commenttime', 'updatetime', 'estimateddeliverymintime',
                               'estimateddeliverymaxtime', 'creationtime', 'estimateddeliverymintime',
                               'estimateddeliverymaxtime', 'endtime', 'starttime']

        self.base_list_nodes = [
            'findhalfproductsresponse.halfcatalogproduct.productid',
            'findhalfproductsresponse.halfproducts.product',
            'getshippingcostsresponse.internationalshippingserviceoption.shipsto',
            'getsingleitemresponse.itemcompatibility.compatibility',
            'getsingleitemresponse.itemcompatibility.namevaluelist',
            'getsingleitemresponse.variationspecifics.namevaluelist',
            'getsingleitemresponse.namevaluelist.value',
            'getsingleitemresponse.pictures.variationspecificpictureset',
            'getmultipleitemsresponse.pictures.variationspecificpictureset',
            'findreviewsandguidesresponse.reviewdetails.review',
            'getshippingcostsresponse.shippingdetails.internationalshippingserviceoption',
            'getshippingcostsresponse.shippingdetails.shippingserviceoption',
            'getshippingcostsresponse.shippingdetails.excludeshiptolocation',
            'getshippingcostsresponse.shippingserviceoption.shipsto',
            'findpopularitemsresponse.itemarray.item',
            'findproductsresponse.itemarray.item',
            'getsingleitemresponse.item.paymentmethods',
            'getmultipleitemsresponse.item.pictureurl',
            'getsingleitemresponse.item.pictureurl',
            'findproductsresponse.item.shiptolocations',
            'getmultipleitemsresponse.item.shiptolocations',
            'getsingleitemresponse.item.shiptolocations',
            'getmultipleitemsresponse.item.paymentallowedsite',
            'getsingleitemresponse.item.paymentallowedsite',
            'getsingleitemresponse.item.excludeshiptolocation',
            'getshippingcostsresponse.taxtable.taxjurisdiction',
            'getsingleitemresponse.variationspecificpictureset.pictureurl',
            'getmultipleitemsresponse.variationspecificpictureset.pictureurl',
            'getsingleitemresponse.variations.variation',
            'getmultipleitemsresponse.variations.variation',
            'getsingleitemresponse.variations.pictures',
            'getmultipleitemsresponse.variations.pictures',
        ]

    def build_request_headers(self, verb):
        headers = {
            "X-EBAY-API-VERSION": self.config.get('version', ''),
            "X-EBAY-API-APP-ID": self.config.get('appid', ''),
            "X-EBAY-API-SITE-ID": self.config.get('siteid', ''),
            "X-EBAY-API-CALL-NAME": verb,
            "X-EBAY-API-REQUEST-ENCODING": "XML",
            "Content-Type": "text/xml"
        }

        if self.config.get('trackingid'):
            headers.update({
                "X-EBAY-API-TRACKING-ID": self.config.get('trackingid')
            })

        if self.config.get('trackingpartnercode'):
            headers.update({
                "X-EBAY-API-TRACKING-PARTNER-CODE": self.config.get('trackingpartnercode')
            })

        return headers

    def build_request_data(self, verb, data, verb_attrs):

        xml = "<?xml version='1.0' encoding='utf-8'?>"
        xml += "<" + verb + "Request xmlns=\"urn:ebay:apis:eBLBaseComponents\">"
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

        for e in dom.findall('Errors'):
            eSeverity = None
            eClass = None
            eShortMsg = None
            eLongMsg = None
            eCode = None

            try:
                eSeverity = e.findall('SeverityCode')[0].text
            except IndexError:
                pass

            try:
                eClass = e.findall('ErrorClassification')[0].text
            except IndexError:
                pass

            try:
                eCode = e.findall('ErrorCode')[0].text
            except IndexError:
                pass

            try:
                eShortMsg = e.findall('ShortMessage')[0].text
            except IndexError:
                pass

            try:
                eLongMsg = e.findall('LongMessage')[0].text
            except IndexError:
                pass

            try:
                eCode = float(e.findall('ErrorCode')[0].text)
                if eCode.is_integer():
                    eCode = int(eCode)

                if eCode not in resp_codes:
                    resp_codes.append(eCode)
            except IndexError:
                pass

            msg = "Class: %s, Severity: %s, Code: %s, %s%s" \
                % (eClass, eSeverity, eCode, eShortMsg, eLongMsg)

            if eSeverity == 'Warning':
                warnings.append(msg)
            else:
                errors.append(msg)

        self._resp_body_warnings = warnings
        self._resp_body_errors = errors
        self._resp_codes = resp_codes

        if self.config.get('warnings') and len(warnings) > 0:
            log.warn("%s: %s\n\n" % (self.verb, "\n".join(warnings)))

        if self.response.reply.Ack == 'Failure':
            if self.config.get('errors'):
                log.error("%s: %s\n\n" % (self.verb, "\n".join(errors)))
            return errors

        return []
