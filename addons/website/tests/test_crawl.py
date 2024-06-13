# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import time

import lxml.html
from werkzeug import urls

import odoo

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
        self.env.ref('website.default_website').write({
            'social_facebook': "https://www.facebook.com/Odoo",
            'social_twitter': 'https://twitter.com/Odoo',
            'social_linkedin': 'https://www.linkedin.com/company/odoo',
            'social_youtube': 'https://www.youtube.com/user/OpenERPonline',
            'social_github': 'https://github.com/odoo',
            'social_instagram': 'https://www.instagram.com/explore/tags/odoo/',
            'social_tiktok': 'https://www.tiktok.com/@odoo',
        })

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

    def clean_url(self, url):
        # convert <slug>
        clean_url = re.sub(r"(?<=/)(([^/=?&]+)?-?[0-9]+)(?=(/|$|\?|#))", r"<slug>", url)

        # remove # part, sort param and clean trailing /?
        base, *qs = clean_url.split('#', 1)[0].split('?', 1)
        qs_sorted = '?' + '&'.join(sorted(''.join(qs).split('&')))

        # convert ?qs=<param>
        qs_sorted = re.sub(r"([^=?&]+)=[^=?&]+", r'\g<1>=<param>', qs_sorted)
        clean_url = base.rstrip('/#') + qs_sorted.rstrip('?#')

        return clean_url

    def crawl(self, url, seen=None, msg=''):
        if seen is None:
            seen = set()

        url_slug = self.clean_url(url)

        if url_slug in seen:
            return seen
        seen.add(url_slug)

        _logger.info("%s %s", msg, url)
        r = self.url_open(url, allow_redirects=False)
        if r.status_code in (301, 302, 303):
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
                    parts.path.startswith('/en/') or \
                   (parts.scheme and parts.scheme not in ('http', 'https')):
                    continue

                self.crawl(href, seen, msg)
        return seen

    def test_05_test_clean_url(self):
        urls_to_check = [
            ("/my/1/20/300", "/my/<slug>/<slug>/<slug>"),
            ("/my/19/", "/my/<slug>"),
            ("/my/19#", "/my/<slug>"),
            ("/my/19#a=b", "/my/<slug>"),
            ("/my/19/?access_token=www-xxx-yyy-zzz", "/my/<slug>?access_token=<param>"),
            ("/my/19?access_token=www-xxx-yyy-zzz", "/my/<slug>?access_token=<param>"),
            ("/my/19?access_token=www-xxx-yyy-zzz&report_type=pdf", "/my/<slug>?access_token=<param>&report_type=<param>"),
            ("/my/slug-19/", "/my/<slug>"),
            ("/my/slug-19#a=b", "/my/<slug>"),
            ("/my/slug-19/?access_token=www-xxx-yyy-zzz", "/my/<slug>?access_token=<param>"),
            ("/my/slug-19?access_token=www-xxx-yyy-zzz", "/my/<slug>?access_token=<param>"),
            ("/my/slug-19?access_token=www-xxx-yyy-zzz&report_type=pdf", "/my/<slug>?access_token=<param>&report_type=<param>"),
            ("/my/page/2?order=website_sequence+asc", "/my/page/<slug>?order=<param>"),
            ("/my/page/2", "/my/page/<slug>"),
            ("/my/page/2/", "/my/page/<slug>"),
            ("/terms", "/terms"),
            ("/controller/slug-1", "/controller/<slug>"),
            ("/controller/tag/slug-2", "/controller/tag/<slug>"),
            ("/controller/slug-1/slug-2", "/controller/<slug>/<slug>"),
            ("/controller/slug-1/tag/slug-2", "/controller/<slug>/tag/<slug>"),
            ("/controller/slug-1/tag/slug-2/end", "/controller/<slug>/tag/<slug>/end"),
            ("/controller?tags=%5B5%5D", "/controller?tags=<param>"),
            ("/controller?date=upcoming&tags=%5B5%5D", "/controller?date=<param>&tags=<param>"),
            ("/controller?tags=%5B%5D&date=upcoming", "/controller?date=<param>&tags=<param>"),
            ("/controller?tags=%5B%5D&from=/a/b/c", "/controller?from=<param>&tags=<param>"),
            ("/controller?tags=%5B%5D&from=d/e/f&to=/a/b", "/controller?from=<param>&tags=<param>&to=<param>"),
            ("/controller?tags=%5B%5D&from=d/e/f&to=/c/d", "/controller?from=<param>&tags=<param>&to=<param>"),
        ]
        uniq = set()
        for url, clean_expected in urls_to_check:
            cleaned = self.clean_url(url)
            self.assertEqual(cleaned, clean_expected)
            uniq.add(cleaned)
        self.assertEqual(len(uniq), 16)

    def test_10_crawl_public(self):
        t0 = time.time()
        t0_sql = self.registry.test_cr.sql_log_count
        seen = self.crawl('/', msg='Anonymous Coward')
        count = len(seen)
        duration = time.time() - t0
        sql = self.registry.test_cr.sql_log_count - t0_sql
        _logger.runbot("public crawled %s urls in %.2fs %s queries, %.3fs %.2fq per request, ", count, duration, sql, duration / count, float(sql) / count)

    def test_20_crawl_demo(self):
        # Demo user without sales/crm/helpdesk/... rights won't be able to access to
        # portals like /my/leads. Grant him those rights if exists.
        groups = self.env['res.groups']
        group_xmlids = [
            'sales_team.group_sale_salesman',
            'purchase.group_purchase_user',
            'helpdesk.group_helpdesk_user',
        ]
        for group_xmlid in group_xmlids:
            group = self.env.ref(group_xmlid, raise_if_not_found=False)
            if group:
                groups += group
        self.env.ref('base.group_user').write({'implied_ids': [(4, group.id) for group in groups]})
        t0 = time.time()
        t0_sql = self.registry.test_cr.sql_log_count
        self.authenticate('demo', 'demo')
        seen = self.crawl('/', msg='demo')
        count = len(seen)
        duration = time.time() - t0
        sql = self.registry.test_cr.sql_log_count - t0_sql
        _logger.runbot("demo crawled %s urls in %.2fs %s queries, %.3fs %.2fq per request", count, duration, sql, duration / count, float(sql) / count)
