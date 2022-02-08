# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

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
                # mark as old
                new_page._write({'write_date': '2020-01-01'})
            else:
                last_5_url_edited.append(new_page.url)

        res = self.opener.post(url=suggested_links_url, json={'params': {'needle': '/'}})
        resp = json.loads(res.content)
        assert 'result' in resp
        suggested_links = resp['result']
        last_modified_history = next(o for o in suggested_links['others'] if o["title"] == "Last modified pages")
        last_modified_values = map(lambda o: o['value'], last_modified_history['values'])

        matching_pages = set(map(lambda o: o['value'], suggested_links['matching_pages']))
        self.assertEqual(set(last_modified_values), set(last_5_url_edited) - matching_pages)
