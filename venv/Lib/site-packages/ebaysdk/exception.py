# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''


class EbaySDKError(Exception):

    def __init__(self, msg, response=None):
        super(EbaySDKError, self).__init__(u'%s' % msg)
        self.message = u'%s' % msg
        self.response = response

    def __str__(self):
        return repr(self.message)


class ConnectionError(EbaySDKError):
    pass


class ConnectionConfigError(EbaySDKError):
    pass


class ConnectionResponseError(EbaySDKError):
    pass


class RequestPaginationError(EbaySDKError):
    pass


class PaginationLimit(EbaySDKError):
    pass
