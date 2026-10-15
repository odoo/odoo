# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import time

import lxml.html
from werkzeug import urls

import odoo
from odoo.tests.common import STATIC_RESOURCE_RE, XMLID_IMAGE_RE, is_cacheable_resource
from odoo.tools import BinaryBytes

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.base.tests.files import PNG_RAW

_logger = logging.getLogger(__name__)

CSS_URL_RE = re.compile(r'url\((?:&quot;|["\'])?([^)"\']+)')
# in characters of the data URI
INLINE_IMAGE_MAX_SIZE = 2048


@odoo.tests.common.tagged('post_install', '-at_install', 'crawl')
class Crawler(HttpCaseWithUserDemo):
    """ Test suite crawling an Odoo CMS instance and checking that all
    internal links lead to a 200 response.

    If a username and a password are provided, authenticates the user before
    starting the crawl
    """

    def setUp(self):
        super(Crawler, self).setUp()
        self.env.ref('base.default_website').company_id.write({
            'social_facebook': "https://www.facebook.com/Odoo",
            'social_twitter': 'https://twitter.com/Odoo',
            'social_linkedin': 'https://www.linkedin.com/company/odoo',
            'social_youtube': 'https://www.youtube.com/user/OpenERPonline',
            'social_github': 'https://github.com/odoo',
            'social_instagram': 'https://www.instagram.com/explore/tags/odoo/',
            'social_tiktok': 'https://www.tiktok.com/@odoo',
            'social_discord': 'https://discord.com/servers/discord-town-hall-169256939211980800',
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

    def _resource_urls(self, doc):
        yield from doc.xpath('//img/@src')
        for value in doc.xpath('//img/@srcset | //source/@srcset'):
            yield from (part.split()[0] for part in value.split(',') if part.strip())
        for link in doc.xpath('//link[@href]'):
            if set(link.get('rel', '').split()) & {'stylesheet', 'icon', 'apple-touch-icon', 'preload', 'image_src'}:
                yield link.get('href')
        for value in doc.xpath('//*/@style'):
            yield from CSS_URL_RE.findall(value)

    def check_resources_cacheable(self, doc, page_url, resources):
        for resource in self._resource_urls(doc):
            if resource.startswith('data:'):
                if len(resource) > INLINE_IMAGE_MAX_SIZE:
                    mimetype = resource[5:].split(';', 1)[0].split(',', 1)[0]
                    resources.setdefault(f'{resource[:40]}...{resource[-8:]} ({len(resource)} chars)', (page_url, '', 'inline', mimetype, ''))
                continue
            parts = urls.url_parse(resource)
            if parts.netloc or parts.scheme or not parts.path.startswith('/') \
                    or STATIC_RESOURCE_RE.match(parts.path) or XMLID_IMAGE_RE.fullmatch(parts.path) \
                    or resource in resources:
                continue
            r = self.url_open(resource, allow_redirects=False)
            target = ''
            # permanent redirects are cached, other ones are requested on every page view
            while r.status_code in (301, 308):
                location = urls.url_parse(r.headers['Location'])
                if location.netloc and location.netloc != urls.url_parse(self.base_url()).netloc:
                    break
                target = location.path
                r = self.url_open(location.replace(scheme='', netloc='').to_url(), allow_redirects=False)
            if r.status_code in (301, 308):
                # permanent redirect to another site, out of scope
                resources[resource] = None
                continue
            resources[resource] = None if is_cacheable_resource(r.headers) else (
                page_url, target, r.status_code, r.headers.get('Content-Type', ''), r.headers.get('Cache-Control', ''))

    def assert_resources_cacheable(self, resources):
        uncacheable = {url: info for url, info in resources.items() if info}
        if uncacheable:
            self.fail("Resources of public pages must be cacheable by CDNs (not private, with a `unique` URL):\n%s" % '\n'.join(
                f"{url}{f' -> {target}' if target else ''}  [{status} {content_type} | {cache_control}]  on {page}"
                for url, (page, target, status, content_type, cache_control) in sorted(uncacheable.items())
            ))

    def crawl(self, url, seen=None, msg='', resources=None):
        if seen is None:
            seen = set()

        url_slug = self.clean_url(url)

        if url_slug in seen:
            return seen
        seen.add(url_slug)

        _logger.info("%s %s", msg, url)
        r = self.url_open(url, allow_redirects=False)
        if r.status_code in (301, 302, 303, 307, 308):
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
            if resources is not None:
                self.check_resources_cacheable(doc, url, resources)
            for link in doc.xpath('//a[@href]'):
                href = link.get('href')

                parts = urls.url_parse(href)
                # href with any fragment removed
                href = parts.replace(fragment='').to_url()

                # FIXME: handle relative link (not parts.path.startswith /)
                if parts.netloc or \
                    not parts.path.startswith('/') or \
                    parts.path == '/odoo' or\
                    parts.path.startswith('/web/') or \
                    parts.path.startswith('/en/') or \
                   (parts.scheme and parts.scheme not in ('http', 'https')):
                    continue

                self.crawl(href, seen, msg, resources)
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
        t0_sql = self.cr.sql_log_count
        resources = {}
        seen = self.crawl('/', msg='Anonymous Coward', resources=resources)
        count = len(seen)
        duration = time.time() - t0
        sql = self.cr.sql_log_count - t0_sql
        _logger.runbot("public crawled %s urls in %.2fs %s queries, %.3fs %.2fq per request, ", count, duration, sql, duration / count, float(sql) / count)

        self.assert_resources_cacheable(resources)

    def test_15_custom_lang_flag_cacheable(self):
        lang_fr = self.env['res.lang']._activate_lang('fr_FR')
        lang_fr.flag_image = BinaryBytes(PNG_RAW)
        self.env.ref('base.default_website').language_ids |= lang_fr
        self.env.ref('website.footer_language_selector_flag').active = True

        doc = lxml.html.fromstring(self.url_open('/').content)
        resources = {}
        self.check_resources_cacheable(doc, '/', resources)
        self.assertTrue(any(url.startswith(f'/web/image/res.lang/{lang_fr.id}/flag_image') for url in resources))
        self.assert_resources_cacheable(resources)

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
        t0_sql = self.cr.sql_log_count
        self.authenticate('demo', 'demo')
        seen = self.crawl('/', msg='demo')
        count = len(seen)
        duration = time.time() - t0
        sql = self.cr.sql_log_count - t0_sql
        _logger.runbot("demo crawled %s urls in %.2fs %s queries, %.3fs %.2fq per request", count, duration, sql, duration / count, float(sql) / count)
