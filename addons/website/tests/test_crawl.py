# -*- coding: utf-8 -*-
import logging
import urlparse
import unittest2
import urllib2
import werkzeug.urls

import lxml.html

import openerp
from openerp import tools

_logger = logging.getLogger(__name__)

class Crawler(openerp.tests.HttpCase):
    """ Test suite crawling an openerp CMS instance and checking that all
    internal links lead to a 200 response.

    If a username and a password are provided, authenticates the user before
    starting the crawl
    """

    at_install = False
    post_install = True

    def crawl(self, url, seen=None, msg=''):
        if seen ==  None:
            seen = set()

        _logger.info("%s %s", msg, url)
        r = self.url_open(url)
        code = r.getcode()
        self.assertIn( code, xrange(200, 300), "%s Fetching %s returned error response (%d)" % (msg, url, code))

        if r.info().gettype() == 'text/html':
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

                # FIXME: handle relative link (not parts.path.startswith /)
                if parts.netloc or \
                    not parts.path.startswith('/') or \
                    parts.path == '/web' or\
                    parts.path.startswith('/web/') or \
                    (parts.scheme and parts.scheme not in ('http', 'https')):
                    continue

                if href not in seen:
                    seen.add(url)
                    self.crawl(href, seen, msg)

    def test_10_crawl_public(self):
        self.crawl('/', msg='Anonymous Coward')

    def test_20_crawl_demo(self):
        self.authenticate('demo', 'demo')
        self.crawl('/', msg='demo')

    def test_30_crawl_admin(self):
        self.authenticate('admin', 'admin')
        self.crawl('/', msg='admin')

