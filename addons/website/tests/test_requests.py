# -*- coding: utf-8 -*-
import urlparse
import unittest2
import urllib2
import werkzeug.urls

import lxml.html

import openerp
from openerp import tools

import cases

__all__ = ['load_tests', 'CrawlSuite']

class RedirectHandler(urllib2.HTTPRedirectHandler):
    """
    HTTPRedirectHandler is predicated upon HTTPErrorProcessor being used and
    works by intercepting 3xy "errors".

    Inherit from it to handle 3xy non-error responses instead, as we're not
    using the error processor
    """

    def http_response(self, request, response):
        code, msg, hdrs = response.code, response.msg, response.info()

        if 300 <= code < 400:
            return self.parent.error(
                'http', request, response, code, msg, hdrs)

        return response

    https_response = http_response

class CrawlSuite(unittest2.TestSuite):
    """ Test suite crawling an openerp CMS instance and checking that all
    internal links lead to a 200 response.

    If a username and a password are provided, authenticates the user before
    starting the crawl
    """

    at_install = False
    post_install = True

    def __init__(self, user=None, password=None):
        super(CrawlSuite, self).__init__()

        registry = openerp.registry(tools.config['db_name'])
        try:
            # switch registry to test mode, so that requests can be made
            registry.enter_test_mode()

            self.opener = urllib2.OpenerDirector()
            self.opener.add_handler(urllib2.UnknownHandler())
            self.opener.add_handler(urllib2.HTTPHandler())
            self.opener.add_handler(urllib2.HTTPSHandler())
            self.opener.add_handler(urllib2.HTTPCookieProcessor())
            self.opener.add_handler(RedirectHandler())

            self._authenticate(user, password)
            self.user = user

        finally:
            registry.leave_test_mode()

    def _request(self, path):
        return self.opener.open(urlparse.urlunsplit([
            'http', 'localhost:%s' % tools.config['xmlrpc_port'],
            path, '', ''
        ]))

    def _authenticate(self, user, password):
        # force tools.config['db_name'] in user session so opening `/` doesn't
        # blow up in multidb situations
        self.opener.open('http://localhost:{port}/web/?db={db}'.format(
            port=tools.config['xmlrpc_port'],
            db=werkzeug.urls.url_quote_plus(tools.config['db_name']),
        ))
        if user is not None:
            url = 'http://localhost:{port}/login?{query}'.format(
                port=tools.config['xmlrpc_port'],
                query=werkzeug.urls.url_encode({
                    'db': tools.config['db_name'],
                    'login': user,
                    'key': password,
                })
            )
            auth = self.opener.open(url)
            assert auth.getcode() < 400, "Auth failure %d" % auth.getcode()

    def _wrapped_run(self, result, debug=False):
        registry = openerp.registry(tools.config['db_name'])
        try:
            # switch registry to test mode, so that requests can be made
            registry.enter_test_mode()

            paths = [URL('/')]
            seen = set(paths)

            while paths:
                url = paths.pop(0)
                r = self._request(url.url)
                url.to_case(self.user, r).run(result)

                if r.info().gettype() != 'text/html':
                    continue

                doc = lxml.html.fromstring(r.read())
                for link in doc.xpath('//a[@href]'):
                    href = link.get('href')

                    parts = urlparse.urlsplit(href)
                    # href with any fragment removed
                    href = urlparse.urlunsplit((
                        parts.scheme,
                        parts.netloc,
                        parts.path,
                        parts.query,
                        ''
                    ))

                    # avoid repeats, even for links we won't crawl no need to
                    # bother splitting them if we've already ignored them
                    # previously
                    if href in seen: continue
                    seen.add(href)

                    # FIXME: handle relative link (not parts.path.startswith /)
                    if parts.netloc or \
                        not parts.path.startswith('/') or \
                        parts.path == '/web' or\
                        parts.path.startswith('/web/') or \
                        (parts.scheme and parts.scheme not in ('http', 'https')):
                        continue

                    paths.append(URL(href, url.url))

        finally:
            registry.leave_test_mode()

class URL(object):
    def __init__(self, url, source=None):
        self.url = url
        self.source = source

    def to_case(self, user, result):
        return cases.URLCase(user, self.url, self.source, result)

def load_tests(loader, base, _):
    base.addTest(CrawlSuite())
    base.addTest(CrawlSuite('admin', 'admin'))
    base.addTest(CrawlSuite('demo', 'demo'))
    return base
