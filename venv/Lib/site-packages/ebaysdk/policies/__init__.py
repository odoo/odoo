# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

from ebaysdk import log
from ebaysdk.connection import BaseConnection
from ebaysdk.config import Config
from ebaysdk.utils import dict2xml


class Connection(BaseConnection):
    """Connection class for the Business Policies service

    API documentation:
    http://developer.ebay.com/Devzone/business-policies

    Supported calls:
    addSellerProfile
    getSellerProfiles
    (all others, see API docs)

    """

    def __init__(self, **kwargs):
        """Finding class constructor.

        Keyword arguments:
        domain        -- API endpoint (default: svcs.ebay.com)
        config_file   -- YAML defaults (default: ebay.yaml)
        debug         -- debugging enabled (default: False)
        warnings      -- warnings enabled (default: False)
        uri           -- API endpoint uri (default: /services/selling/v1/SellerProfilesManagementService)
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
        self.config.set(
            'uri', '/services/selling/v1/SellerProfilesManagementService')
        self.config.set('https', True)
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
        self.config.set('version', '1.0.0')
        self.config.set('service', 'SellerProfilesManagementService')
        self.config.set(
            'doc_url', 'http://developer.ebay.com/Devzone/business-policies/CallRef/index.html')

        self.datetime_nodes = ['deleteddate', 'timestamp', 'maxdeliverydate',
                               'mindeliverydate']
        self.base_list_nodes = [
            'setsellerprofileresponse.paymentprofile.categorygroups.categorygroup',
            'addsellerprofileresponse.paymentprofile.categorygroups.categorygroup',
            'getsellerprofilesresponse.paymentprofilelist.paymentprofile.categorygroups.categorygroup',
            'addsellerprofileresponse.returnpolicyprofile.categorygroups.categorygroup',
            'setsellerprofileresponse.returnpolicyprofile.categorygroups.categorygroup',
            'getsellerprofilesresponse.returnpolicyprofilelist.returnpolicyprofile.categorygroups.categorygroup',
            'addsellerprofileresponse.shippingpolicyprofile.categorygroups.categorygroup',
            'setsellerprofileresponse.shippingpolicyprofile.categorygroups.categorygroup',
            'getsellerprofilesresponse.shippingpolicyprofilelist.shippingpolicyprofile.categorygroups.categorygroup',
            'consolidateshippingprofilesresponse.consolidationjob',
            'getconsolidationjobstatusresponse.consolidationjob',
            'addsellerprofileresponse.paymentprofile.paymentinfo.depositdetails',
            'setsellerprofileresponse.paymentprofile.paymentinfo.depositdetails',
            'getsellerprofilesresponse.paymentprofilelist.paymentprofile.paymentinfo.depositdetails',
            'addsellerprofileresponse.shippingpolicyprofile.shippingpolicyinfo.freightshipping',
            'setsellerprofileresponse.shippingpolicyprofile.shippingpolicyinfo.freightshipping',
            'getsellerprofilesresponse.shippingpolicyprofilelist.shippingpolicyprofile.shippingpolicyinfo.freightshipping',
            'addsellerprofileresponse.shippingpolicyprofile.shippingpolicyinfo.insurance',
            'setsellerprofileresponse.shippingpolicyprofile.shippingpolicyinfo.insurance',
            'getsellerprofilesresponse.shippingpolicyprofilelist.shippingpolicyprofile.shippingpolicyinfo.insurance',
            'addsellerprofileresponse.paymentprofile.paymentinfo',
            'setsellerprofileresponse.paymentprofile.paymentinfo',
            'getsellerprofilesresponse.paymentprofilelist.paymentprofile.paymentinfo',
            'addsellerprofileresponse.returnpolicyprofile.returnpolicyinfo',
            'setsellerprofileresponse.returnpolicyprofile.returnpolicyinfo',
            'getsellerprofilesresponse.returnpolicyprofilelist.returnpolicyprofile.returnpolicyinfo',
            'addsellerprofileresponse.sellerprofile',
            'setsellerprofileresponse.sellerprofile',
            'getsellerprofilesresponse.paymentprofilelist.sellerprofile',
            'getsellerprofilesresponse.returnpolicyprofilelist.sellerprofile',
            'getsellerprofilesresponse.shippingpolicyprofilelist.sellerprofile',
            'addsellerprofileresponse.shippingpolicyprofile.shippingpolicyinfo.shippingpolicyinfoservice',
            'setsellerprofileresponse.shippingpolicyprofile.shippingpolicyinfo.shippingpolicyinfoservice',
            'getsellerprofilesresponse.shippingpolicyprofilelist.shippingpolicyprofile.shippingpolicyinfo.shippingpolicyinfoservice',
            'addsellerprofileresponse.shippingpolicyprofile.shippingpolicyinfo.shippingprofilediscountinfo',
            'setsellerprofileresponse.shippingpolicyprofile.shippingpolicyinfo.shippingprofilediscountinfo',
            'getsellerprofilesresponse.shippingpolicyprofilelist.shippingpolicyprofile.shippingpolicyinfo.shippingprofilediscountinfo'
        ]

    def build_request_headers(self, verb):
        return {
            "X-EBAY-SOA-SERVICE-NAME": self.config.get('service', ''),
            "X-EBAY-SOA-SERVICE-VERSION": self.config.get('version', ''),
            "X-EBAY-SOA-SECURITY-TOKEN": self.config.get('token', ''),
            "X-EBAY-SOA-GLOBAL-ID": self.config.get('siteid', ''),
            "X-EBAY-SOA-OPERATION-NAME": verb,
            "X-EBAY-SOA-REQUEST-DATA-FORMAT": self.config.get('request_encoding', ''),
            "X-EBAY-SOA-RESPONSE-DATA-FORMAT": self.config.get('response_encoding', ''),
            "Content-Type": "text/xml"
        }

    def build_request_data(self, verb, data, verb_attrs):
        xml = "<?xml version='1.0' encoding='utf-8'?>"
        xml += "<{verb}Request xmlns=\"http://www.ebay.com/marketplace/selling/v1/services\">".format(
            verb=verb)
        xml += dict2xml(data, self.escape_xml)
        xml += "</{verb}Request>".format(verb=verb)

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
