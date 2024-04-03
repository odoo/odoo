# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''
import sys
from ebaysdk.exception import ConnectionError
import grequests

if sys.version_info[0] >= 3:
    raise ImportError('grequests does not work with python3+')


class Parallel(object):
    """
    >>> from ebaysdk.finding import Connection as finding
    >>> from ebaysdk.shopping import Connection as shopping
    >>> from ebaysdk.http import Connection as html
    >>> import os
    >>> p = Parallel()
    >>> r1 = html(parallel=p)
    >>> retval = r1.execute('http://feeds.feedburner.com/slashdot/audio?format=xml')
    >>> r2 = finding(parallel=p, config_file=os.environ.get('EBAY_YAML'))
    >>> retval = r2.execute('findItemsAdvanced', {'keywords': 'shoes'})
    >>> r3 = shopping(parallel=p, config_file=os.environ.get('EBAY_YAML'))
    >>> retval = r3.execute('FindItemsAdvanced', {'CharityID': 3897})
    >>> p.wait()
    >>> print(p.error())
    None
    >>> print(r1.response.reply.rss.channel.ttl)
    2
    >>> print(r2.response.dict()['ack'])
    Success
    >>> print(r3.response.reply.Ack)
    Success
    """

    def __init__(self):
        self._grequests = []
        self._requests = []
        self._errors = []

    def _add_request(self, request):
        self._requests.append(request)

    def wait(self, timeout=20):
        "wait for all of the api requests to complete"

        self._errors = []
        self._grequests = []

        try:
            for r in self._requests:
                req = grequests.request(r.request.method,
                                        r.request.url,
                                        data=r.request.body,
                                        headers=r.request.headers,
                                        verify=False,
                                        proxies=r.proxies,
                                        timeout=r.timeout,
                                        allow_redirects=True)

                self._grequests.append(req)

            def exception_handler(request, exception):
                self._errors.append("%s" % exception)

            gresponses = grequests.map(
                self._grequests, exception_handler=exception_handler)

            for idx, r in enumerate(self._requests):
                r.response = gresponses[idx]
                r.process_response()
                r.error_check()

                if r.error():
                    self._errors.append(r.error())

        except ConnectionError as e:
            self._errors.append("%s" % e)

        self._requests = []

    def error(self):
        "builds and returns the api error message"

        if len(self._errors) > 0:
            return "parallel error:\n%s\n" % ("\n".join(self._errors))

        return None


if __name__ == '__main__':

    import doctest
    import sys

    failure_count, test_count = doctest.testmod()
    sys.exit(failure_count)
