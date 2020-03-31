# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time

import lxml.html
from werkzeug import urls

import odoo
import re

from odoo.addons.base.tests.common import HttpCaseWithUserDemo

_logger = logging.getLogger(__name__)


@odoo.tests.common.tagged('post_install', '-at_install', 'crawl')
class Crawler(HttpCaseWithUserDemo):
    """ Test suite crawling an Odoo CMS instance and checking that all
    internal links lead to a 200 response.

    If a username and a password are provided, authenticates the user before
    starting the crawl
    """

    def setUp(self):
        super(Crawler, self).setUp()

        if hasattr(self.env['res.partner'], 'grade_id'):
            # Create at least one published parter, so that /partners doesn't
            # return a 404
            grade = self.env['res.partner.grade'].create({
                'name': 'A test grade',
                'website_published': True,
            })
            self.env['res.partner'].create({
                'name': 'A Company for /partners',
                'is_company': True,
                'grade_id': grade.id,
                'website_published': True,
            })

    def crawl(self, url, seen=None, msg=''):
        if seen is None:
            seen = set()

        url_slug = re.sub(r"[/](([^/=?&]+-)?[0-9]+)([/]|$)", '/<slug>/', url)
        url_slug = re.sub(r"([^/=?&]+)=[^/=?&]+", '\g<1>=param', url_slug)
        if url_slug in seen:
            return seen
        else:
            seen.add(url_slug)

        _logger.info("%s %s", msg, url)
        r = self.url_open(url, allow_redirects=False)
        if r.status_code in (301, 302):
            # check local redirect to avoid fetch externals pages
            new_url = r.headers.get('Location')
            current_url = r.url
            if urls.url_parse(new_url).netloc != urls.url_parse(current_url).netloc:
                return seen
            r = self.url_open(new_url)

        code = r.status_code
        self.assertIn(code, range(200, 300), "%s Fetching %s returned error response (%d)" % (msg, url, code))

        if r.headers['Content-Type'].startswith('text/html'):
            doc = lxml.html.fromstring(r.content)
            for link in doc.xpath('//a[@href]'):
                href = link.get('href')

                parts = urls.url_parse(href)
                # href with any fragment removed
                href = parts.replace(fragment='').to_url()

                # FIXME: handle relative link (not parts.path.startswith /)
                if parts.netloc or \
                    not parts.path.startswith('/') or \
                    parts.path == '/web' or\
                    parts.path.startswith('/web/') or \
                    parts.path.startswith('/en_US/') or \
                    (parts.scheme and parts.scheme not in ('http', 'https')):
                    continue

                self.crawl(href, seen, msg)
        return seen

    def test_10_crawl_public(self):
        t0 = time.time()
        t0_sql = self.registry.test_cr.sql_log_count
        seen = self.crawl('/', msg='Anonymous Coward')
        count = len(seen)
        duration = time.time() - t0
        sql = self.registry.test_cr.sql_log_count - t0_sql
        _logger.runbot("public crawled %s urls in %.2fs %s queries, %.3fs %.2fq per request, ", count, duration, sql, duration / count, float(sql) / count)

    def test_20_crawl_demo(self):
        t0 = time.time()
        t0_sql = self.registry.test_cr.sql_log_count
        self.authenticate('demo', 'demo')
        seen = self.crawl('/', msg='demo')
        count = len(seen)
        duration = time.time() - t0
        sql = self.registry.test_cr.sql_log_count - t0_sql
        _logger.runbot("demo crawled %s urls in %.2fs %s queries, %.3fs %.2fq per request", count, duration, sql, duration / count, float(sql) / count)

    def test_30_crawl_admin(self):
        t0 = time.time()
        t0_sql = self.registry.test_cr.sql_log_count
        self.authenticate('admin', 'admin')
        seen = self.crawl('/', msg='admin')
        count = len(seen)
        duration = time.time() - t0
        sql = self.registry.test_cr.sql_log_count - t0_sql
        _logger.runbot("admin crawled %s urls in %.2fs %s queries, %.3fs %.2fq per request", count, duration, sql, duration / count, float(sql) / count)
