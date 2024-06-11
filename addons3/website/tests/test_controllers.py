# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from werkzeug.urls import url_encode

from odoo import tests
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
