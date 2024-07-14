# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# This file override the method/class coming from the ebaysdk package that
# are not python3 compatible.
# In order to make it work, we need to override the problematic function and
# class that uses `basestring` and sometimes encode a dict

import uuid
import sys

from ebaysdk.exception import EbaySDKError
from ebaysdk.trading import Connection
from ebaysdk import UserAgent
from requests import Request

from odoo import _
from odoo.exceptions import UserError

def smart_encode_request_data(value):
    try:
        if sys.version_info[0] < 3:
            return value

        # Odoo: This line got fixed
        if isinstance(value,str):
            return value.encode('utf-8')
        else:
            return value

    except UnicodeDecodeError:
        return value


class Trading(Connection):
    def build_request(self, verb, data, verb_attrs, files=None):
        self.verb = verb
        self._request_dict = data
        self._request_id = uuid.uuid4()

        url = self.build_request_url(verb)

        headers = self.build_request_headers(verb)
        headers.update({'User-Agent': UserAgent,
                        'X-EBAY-SDK-REQUEST-ID': str(self._request_id)})

        # if we are adding files, we ensure there is no Content-Type header already defined
        # otherwise Request will use the existing one which is likely not to be multipart/form-data
        # data must also be a dict so we make it so if needed

        requestData = self.build_request_data(verb, data, verb_attrs)
        if files:
            del(headers['Content-Type'])
            # Odoo: This line got fixed
            if isinstance(requestData, str):  # pylint: disable-msg=E0602
                requestData = {'XMLPayload': requestData}

        request = Request(self.method,
                          url,
                          data=smart_encode_request_data(requestData),
                          headers=headers,
                          files=files,
                          )

        self.request = request.prepare()


class EbayConnection:
    def __init__(self, **kwargs):
        self.__obj = Trading(**kwargs)

    def execute(self, *args, **kwargs):
        try:
            response = self.__obj.execute(*args, **kwargs)
            return EbayConnectionResponse(response)
        except EbaySDKError as e:
            raise EbayConnectionError(e)
        except AttributeError:
            # Catch non deterministic error from the eBay SDK
            raise UserError(_(
                "An unexpected error occured from eBay.\n"
                "Please check your credentials and try again later."
            ))


class EbayConnectionResponse:
    def __init__(self, response):
        self.dict = response.dict
        self.text = response.text


class EbayConnectionError(Exception):
    def __init__(self, exception):
        super().__init__(exception.message)
        self.response = EbayConnectionResponse(exception.response)
