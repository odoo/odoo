# -*- coding: utf-8 -*-

'''
Authored by: Michal Hernas
Licensed under CDDL 1.0
'''

import os

from ebaysdk import log
from ebaysdk.connection import BaseConnection
from ebaysdk.exception import ConnectionError
from ebaysdk.config import Config
from ebaysdk.utils import dict2xml, smart_encode


class Connection(BaseConnection):
    """Connection class for the Inventory Management service

    API documentation:
    http://developer.ebay.com/Devzone/store-pickup/InventoryManagement/index.html

    Supported calls:
    AddInventory
    AddInventoryLocation
    DeleteInventory
    DeleteInventoryLocation
    (all others, see API docs)

    Doctests:
    Create location first
    >>> f = Connection(config_file=os.environ.get('EBAY_YAML'), debug=False)

    Take care here, unicode string is put here specially to ensure lib can handle it properly. If not we got an error:
    UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3 in position 28: ordinal not in range(128)
    >>> try:
    ...     retval = f.execute(u'AddInventoryLocation', {
    ...         'Address1': u'Alexanderplatz 12 ąśćł',
    ...         'Address2': u'Gebaude 6',
    ...         'City': u'Berlin',
    ...         'Country': u'DE',
    ...         'PostalCode': u'13355',
    ...         'Latitude': u'37.374488',
    ...         'Longitude': u'-122.032876',
    ...         'LocationID': u'ebaysdk_test',
    ...         'LocationType': u'STORE',
    ...         'Phone': u'(408)408-4080',
    ...         'URL': u'http://store.com',
    ...         'UTCOffset': u'+02:00',
    ...         'Name': 'Test',
    ...         'Region': 'Berlin',
    ...         'PickupInstructions': 'Pick it up soon',
    ...         'Hours': [{'Day': {'DayOfWeek': 1, 'Interval': {'Open': '08:00:00', 'Close': '10:00:00'}}}]
    ...     })
    ...     print(f.response.reply.LocationID.lower())
    ... except ConnectionError as e:
    ...     print(f.error()) # doctest: +SKIP
    ebaysdk_test

    And now add item it it
    >>> try:
    ...     f = Connection(config_file=os.environ.get('EBAY_YAML'), debug=False)
    ...     retval = f.execute('AddInventory', {"SKU": "SKU_TEST", "Locations": {"Location": [
    ...     {"Availability": "IN_STOCK", "LocationID": "ebaysdk_test", "Quantity": 10}
    ...     ]}})
    ...     print(f.response.reply.SKU.lower())
    ... except ConnectionError as e:
    ...     print(f.error()) # doctest: +SKIP
    sku_test


    Delete item from all locations
    >>> try:
    ...     f = Connection(config_file=os.environ.get('EBAY_YAML'), debug=False)
    ...     retval = f.execute('DeleteInventory', {"SKU": "SKU_TEST", "Confirm": 'true'})
    ...     print(f.response.reply.SKU.lower())
    ... except ConnectionError as e:
    ...     print(f.error()) # doctest: +SKIP
    sku_test


    Delete location
    >>> try:
    ...     f = Connection(config_file=os.environ.get('EBAY_YAML'), debug=False)
    ...     retval = f.execute('DeleteInventoryLocation', {"LocationID": "ebaysdk_test"})
    ...     print(f.response.reply.LocationID.lower())
    ... except ConnectionError as e:
    ...     print(f.error()) # doctest: +SKIP
    ebaysdk_test


    Check errors handling
    >>> try:
    ...     f = Connection(token='WRONG TOKEN', config_file=os.environ.get('EBAY_YAML'), debug=False, errors=True)
    ...     retval = f.execute('DeleteInventoryLocation', {"LocationID": "ebaysdk_test"})
    ... except ConnectionError as e:
    ...     print(f.error()) # doctest: +SKIP
    DeleteInventoryLocation: Bad Request, Class: RequestError, Severity: Error, Code: 503, Authentication: Invalid user token Authentication: Invalid user token


    Sometimes ebay returns us really weird error message, already reported to ebay, if it will be fixed I will remove
    all special cases to handle it.
    Example of wrong response:
    <?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://www.w3.org/2003/05/soap-envelope">
       <soapenv:Body>
          <Response>
             <Timestamp>Wed May 06 2015 02:15:49 GMT-0700 (GMT-07:00)</Timestamp>
             <Ack>Failure</Ack>
             <Errors>
                <ShortMessage>Gateway Error</ShortMessage>
                <LongMessage>Failover endpoint : Selling_Inventory_REST_SVC_V1 - no ready child endpoints</LongMessage>
                <ErrorCode>99.99</ErrorCode>
                <SeverityCode>Error</SeverityCode>
                <ErrorClassification>RequestError</ErrorClassification>
             </Errors>
             <ResponseCode>null</ResponseCode>
             <Version>653</Version>
          </Response>
       </soapenv:Body>
    </soapenv:Envelope>
    """

    def __init__(self, **kwargs):
        """Inventory Management class constructor.

        Keyword arguments:
        domain        -- API endpoint (default: api.ebay.com)
        config_file   -- YAML defaults (default: ebay.yaml)
        debug         -- debugging enabled (default: False)
        warnings      -- warnings enabled (default: False)
        uri           -- API endpoint uri (default: /selling/inventory/v1)
        token         -- eBay application/user token
        version       -- version number (default: 1.0.0)
        https         -- execute of https (required by this API) (default: True)
        proxy_host    -- proxy hostname
        proxy_port    -- proxy port number
        timeout       -- HTTP request timeout (default: 20)
        parallel      -- ebaysdk parallel object
        response_encoding -- API encoding (default: XML)
        request_encoding  -- API encoding (default: XML)
        """

        super(Connection, self).__init__(method='POST', **kwargs)

        self.config = Config(domain=kwargs.get('domain', 'api.ebay.com'),
                             connection_kwargs=kwargs,
                             config_file=kwargs.get('config_file', 'ebay.yaml'))

        # override yaml defaults with args sent to the constructor
        self.config.set('domain', kwargs.get('domain', 'api.ebay.com'))
        self.config.set('uri', '/selling/inventory/v1')
        self.config.set('https', True)
        self.config.set('warnings', True)
        self.config.set('errors', True)
        self.config.set('siteid', None)
        self.config.set('response_encoding', 'XML')
        self.config.set('request_encoding', 'XML')
        self.config.set('proxy_host', None)
        self.config.set('proxy_port', None)
        self.config.set('token', None)
        self.config.set('iaf_token', None)
        self.config.set('appid', None)
        self.config.set('version', '1.0.0')
        self.config.set('service', 'InventoryManagement')
        self.config.set(
            'doc_url', 'http://developer.ebay.com/Devzone/store-pickup/InventoryManagement/index.html')

        self.datetime_nodes = ['starttimefrom', 'timestamp', 'starttime',
                               'endtime']
        self.base_list_nodes = [
        ]

    endpoints = {
        'addinventorylocation': 'locations/delta/add',
        'addinventory': 'inventory/delta/add',
        'deleteinventory': 'inventory/delta/delete',
        'deleteinventorylocation': 'locations/delta/delete',
    }

    def build_request_url(self, verb):
        url = super(Connection, self).build_request_url(verb)
        endpoint = self.endpoints[verb.lower()]
        return "{0}/{1}".format(url, endpoint)

    def build_request_headers(self, verb):
        return {
            "Authorization": "TOKEN {0}".format(self.config.get('token')),
            "Content-Type": "application/xml"
        }

    def build_request_data(self, verb, data, verb_attrs):
        xml = "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        xml += "<{verb}Request>".format(verb=verb)
        xml += dict2xml(data, self.escape_xml)
        xml += "</{verb}Request>".format(verb=verb)

        return xml

    def warnings(self):
        warning_string = ""

        if len(self._resp_body_warnings) > 0:
            warning_string = "{verb}: {message}" \
                .format(verb=self.verb, message=", ".join(self._resp_body_warnings))

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

        # In special case we get errors in this format...
        if not dom.findall('Errors') and dom.find('Body') is not None:
            dom = dom.find('Body').find('Response')

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
                eCode = e.findall('ErrorCode')[0].text
                try:
                    int_code = int(eCode)
                except ValueError:
                    int_code = None

                if int_code and int_code not in resp_codes:
                    resp_codes.append(int_code)

            except IndexError:
                pass

            msg = "Class: {eClass}, Severity: {severity}, Code: {code}, {shortMsg} {longMsg}" \
                .format(eClass=eClass, severity=eSeverity, code=eCode, shortMsg=smart_encode(eShortMsg),
                        longMsg=smart_encode(eLongMsg))

            if eSeverity == 'Warning':
                warnings.append(msg)
            else:
                errors.append(msg)

        self._resp_body_warnings = warnings
        self._resp_body_errors = errors
        self._resp_codes = resp_codes

        if self.config.get('warnings') and len(warnings) > 0:
            log.warn("{verb}: {message}\n\n".format(
                verb=self.verb, message="\n".join(warnings)))

        # In special case of error 500 on ebay side, we get really weird
        # response so I need to fallback to this one
        Ack = getattr(self.response.reply, 'Ack', None)
        if Ack is None:
            Ack = self.response.reply.Envelope.Body.Response.Ack

        if Ack == 'Failure':
            if self.config.get('errors'):
                log.error("{verb}: {message}\n\n".format(
                    verb=self.verb, message="\n".join(errors)))

            return errors

        return []
