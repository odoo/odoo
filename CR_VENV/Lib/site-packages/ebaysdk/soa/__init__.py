# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

from ebaysdk import log
from ebaysdk.connection import BaseConnection
from ebaysdk.config import Config
from ebaysdk.utils import getNodeText, dict2xml


class Connection(BaseConnection):
    """Connection class for a base SOA service"""

    def __init__(self, app_config=None, site_id='EBAY-US', debug=False, **kwargs):
        """SOA Connection class constructor"""

        super(Connection, self).__init__(method='POST', debug=debug, **kwargs)

        self.config = Config(domain=kwargs.get('domain', ''),
                             connection_kwargs=kwargs,
                             config_file=kwargs.get('config_file', 'ebay.yaml'))

        self.config.set('https', False)
        self.config.set('site_id', site_id)
        self.config.set('content_type', 'text/xml;charset=UTF-8')
        self.config.set('request_encoding', 'XML')
        self.config.set('response_encoding', 'XML')
        self.config.set('message_protocol', 'SOAP12')
        # http://www.ebay.com/marketplace/fundraising/v1/services',
        self.config.set('soap_env_str', '')

        ph = None
        pp = 80
        if app_config:
            self.load_from_app_config(app_config)
            ph = self.config.get('proxy_host', ph)
            pp = self.config.get('proxy_port', pp)

    # override this method, to provide setup through a config object, which
    # should provide a get() method for extracting constants we care about
    # this method should then set the .api_config[] dict (e.g. the comment
    # below)
    def load_from_app_config(self, app_config):
        # self.api_config['domain'] = app_config.get('API_SERVICE_DOMAIN')
        # self.api_config['uri'] = app_config.get('API_SERVICE_URI')
        pass

    # Note: this method will always return at least an empty object_dict!
    #   It used to return None in some cases. If you get an empty dict,
    #   you can use the .error() method to look for the cause.
    def response_dict(self):
        return self.response.dict()

    def build_request_headers(self, verb):
        return {
            'Content-Type': self.config.get('content_type'),
            'X-EBAY-SOA-SERVICE-NAME': self.config.get('service'),
            'X-EBAY-SOA-OPERATION-NAME': verb,
            'X-EBAY-SOA-GLOBAL-ID': self.config.get('site_id'),
            'X-EBAY-SOA-REQUEST-DATA-FORMAT': self.config.get('request_encoding'),
            'X-EBAY-SOA-RESPONSE-DATA-FORMAT': self.config.get('response_encoding'),
            'X-EBAY-SOA-MESSAGE-PROTOCOL': self.config.get('message_protocol'),
        }

    def build_request_data(self, verb, data, verb_attrs):
        xml = '<?xml version="1.0" encoding="utf-8"?>'
        xml += '<soap:Envelope'
        xml += ' xmlns:soap="http://www.w3.org/2003/05/soap-envelope"'
        xml += ' xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"'
        xml += ' xmlns:ser="%s" >' % self.config.get('soap_env_str')
        xml += '<soap:Body>'
        xml += '<ser:%sRequest>' % verb
        xml += dict2xml(self.soapify(data), self.escape_xml)
        xml += '</ser:%sRequest>' % verb
        xml += '</soap:Body>'
        xml += '</soap:Envelope>'
        return xml

    def soapify(self, xml):
        xml_type = type(xml)
        if xml_type == dict:
            soap = {}
            for k, v in list(xml.items()):
                if k == '@attrs' or k == '#text':
                    soap[k] = v

                # skip nodes that have ns defined
                elif ':' in k:
                    soap[k] = self.soapify(v)
                else:
                    soap['ser:%s' % (k)] = self.soapify(v)

        elif xml_type == list:
            soap = []
            for x in xml:
                soap.append(self.soapify(x))
        else:
            soap = xml
        return soap

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

        <errorMessage xmlns="http://www.ebay.com/marketplace/search/v1/services"><error><errorId>5014</errorId><domain>CoreRuntime</domain><severity>Error</severity><category>System</category><message>
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

        for e in dom.findall('error'):

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
        except AttributeError:
            pass

        return []
