# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from werkzeug.urls import url_encode

from odoo import tests
from odoo.tools import mute_logger


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
        base_url = self.base_url()
        urls = [
            '/',  # Homepage URL (special case)
            '/contactus',  # Regular website.page URL
            '/website/info',  # Controller (!!also testing multi slashes URL!!)
            '/contactus?name=testing',  # Query string URL
        ]
        for url in urls:
            resp = self.url_open(f'/@{url}')
            self.assertEqual(resp.url, base_url + url, "Public user should have landed in the frontend")
        self.authenticate("admin", "admin")
        for url in urls:
            resp = self.url_open(f'/@{url}')
            backend_params = url_encode(dict(action='website.website_preview', path=url))
            self.assertEqual(
                resp.url, f'{base_url}/web#{backend_params}',
                "Internal user should have landed in the backend")
