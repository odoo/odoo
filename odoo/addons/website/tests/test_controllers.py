# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from werkzeug.urls import url_encode

from unittest.mock import patch, Mock
from odoo import tests
from odoo.addons.website.controllers.main import Website
from odoo.tools import mute_logger, submap


@tests.tagged('post_install', '-at_install')
class TestControllers(tests.HttpCase):

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_last_created_pages_autocompletion(self):
        self.authenticate("admin", "admin")
        Page = self.env['website.page']
        last_5_url_edited = []
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        suggested_links_url = base_url + '/website/get_suggested_links'

        old_pages = Page
        for i in range(0, 10):
            new_page = Page.create({
                'name': 'Generic',
                'type': 'qweb',
                'arch': '''
                    <div>content</div>
                ''',
                'key': "test.generic_view-%d" % i,
                'url': "/generic-%d" % i,
                'is_published': True,
            })
            if i % 2 == 0:
                old_pages += new_page
            else:
                last_5_url_edited.append(new_page.url)

        self.opener.post(url=suggested_links_url, json={'params': {'needle': '/'}})
        # mark as old
        old_pages._write({'write_date': '2020-01-01'})

        res = self.opener.post(url=suggested_links_url, json={'params': {'needle': '/'}})
        resp = json.loads(res.content)
        assert 'result' in resp
        suggested_links = resp['result']
        last_modified_history = next(o for o in suggested_links['others'] if o["title"] == "Last modified pages")
        last_modified_values = map(lambda o: o['value'], last_modified_history['values'])

        matching_pages = set(map(lambda o: o['value'], suggested_links['matching_pages']))
        self.assertEqual(set(last_modified_values), set(last_5_url_edited) - matching_pages)

    def test_02_client_action_iframe_url(self):
        urls = [
            '/',  # Homepage URL (special case)
            '/contactus',  # Regular website.page URL
            '/website/info',  # Controller (!!also testing multi slashes URL!!)
            '/contactus?name=testing',  # Query string URL
        ]
        for url in urls:
            resp = self.url_open(f'/@{url}')
            self.assertURLEqual(resp.url, url, "Public user should have landed in the frontend")
        self.authenticate("admin", "admin")
        for url in urls:
            resp = self.url_open(f'/@{url}')
            backend_params = url_encode(dict(action='website.website_preview', path=url))
            self.assertURLEqual(
                resp.url, f'/web#{backend_params}',
                "Internal user should have landed in the backend")

    def test_03_website_image(self):
        attachment = self.env['ir.attachment'].create({
            'name': 'one_pixel.png',
            'datas': 'iVBORw0KGgoAAAANSUhEUgAAAAYAAAAGCAYAAADgzO9IAAAAJElEQVQI'
                     'mWP4/b/qPzbM8Pt/1X8GBgaEAJTNgFcHXqOQMV4dAMmObXXo1/BqAAAA'
                     'AElFTkSuQmCC',
            'public': True,
        })

        res = self.url_open(f'/website/image/ir.attachment/{attachment.id}_unique/raw?download=1')
        res.raise_for_status()

        headers = {
            'Content-Length': '93',
            'Content-Type': 'image/png',
            'Content-Disposition': 'attachment; filename=one_pixel.png',
            'Cache-Control': 'public, max-age=31536000, immutable',
        }
        self.assertEqual(submap(res.headers, headers.keys()), headers)
        self.assertEqual(res.content, attachment.raw)

    def test_04_website_partner_avatar(self):
        partner = self.env['res.partner'].create({'name': "Jack O'Neill"})

        with self.subTest(published=False):
            partner.website_published = False
            res = self.url_open(f'/website/image/res.partner/{partner.id}/avatar_128?download=1')
            self.assertEqual(res.status_code, 404, "Public user should't access avatar of unpublished partners")

        with self.subTest(published=True):
            partner.website_published = True
            res = self.url_open(f'/website/image/res.partner/{partner.id}/avatar_128?download=1')
            self.assertEqual(res.status_code, 200, "Public user should access avatar of published partners")

        with self.subTest(published=True):
            partner.website_published = True
            self.patch(self.env.registry[partner._name].avatar_128, 'groups', 'base.group_system')
            res = self.url_open(f'/website/image/res.partner/{partner.id}/avatar_128?download=1')
            self.assertEqual(
                res.status_code,
                404,
                "Public user shouldn't access record fields with a `groups` even if published"
            )

    @patch('requests.get')
    def test_05_seo_suggest_language_regex(self, mock_get):
        """
        Test the seo_suggest method to verify it properly handles different
        language inputs, sends correct parameters ('hl' for host language and
        'gl' for geolocation) to the Google API, and returns the expected
        suggestions. The test checks a variety of cases including:
        - Regional language codes (e.g., 'en_US', 'fr_FR')
        - Basic language codes (e.g., 'es', 'sr')
        - Language codes with script modifier (e.g., 'sr_RS@latin',
          'zh_CN@pinyin')
        - Empty string input to handle default case
        """

        # Mocking the response from Google API to simulate what would be
        # returned by the seo_suggest method.
        mock_response = Mock()
        mock_response.content = '''<?xml version="1.0"?>
        <toplevel>
            <CompleteSuggestion>
                <suggestion data="test suggestion"/>
            </CompleteSuggestion>
        </toplevel>'''
        mock_get.return_value = mock_response

        # Test cases with different language inputs and expected hl and gl
        # values.
        test_cases = [
            ('en_US', ['en', 'US']),         # US English
            ('fr_FR', ['fr', 'FR']),         # French in France
            ('es', ['es', '']),              # Spanish without country code
            ('sr_RS@latin', ['sr', 'RS']),   # Serbian with script in Serbia
            ('zh_CN@pinyin', ['zh', 'CN']),  # Chinese with pinyin script in China
            ('sr@latin', ['sr', '']),        # Serbian with script but no country
            ('', ['en', 'US'])               # Default case (empty lang. input)
        ]

        for lang_input, expected_output in test_cases:
            # subTest creates an isolated context for each test case, allowing
            # failures to be reported separately.
            with self.subTest(lang=lang_input):
                result = Website.seo_suggest(self, keywords="test", lang=lang_input)

                # Extract the parameters that were passed in the mock
                # requests.get call.
                called_params = mock_get.call_args[1]['params']

                # Verify that the 'hl' parameter (host language) matches the
                # expected output
                self.assertEqual(called_params['hl'], expected_output[0])

                # Verify that the 'gl' parameter (geolocation) matches the
                # expected output
                self.assertEqual(called_params['gl'], expected_output[1])

                # Verify that the returned result contains the expected
                # suggestion "test suggestion"
                self.assertIn('test suggestion', result)
