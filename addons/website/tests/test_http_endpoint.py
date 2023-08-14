# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import sentinel

from odoo.http import EndPoint
from odoo.tests import HttpCase


class TestHttpEndPoint(HttpCase):

    def test_http_endpoint_equality(self):
        sentinel.method.original_func = sentinel.method_original_func
        args = (sentinel.method, {'routing_arg': sentinel.routing_arg})
        endpoint1 = EndPoint(*args)
        endpoint2 = EndPoint(*args)

        self.assertEqual(endpoint1, endpoint2)

        testdict = {}
        testdict[endpoint1] = 42
        self.assertEqual(testdict[endpoint2], 42)
        self.assertTrue(endpoint2 in testdict)

    def test_can_clear_routing_map_during_render(self):
        """
        The routing map might be cleared while rendering a qweb view.
        For example, if an asset bundle is regenerated the old one is unlinked,
        which causes a cache clearing.
        This test ensures that the rendering still works, even in this case.
        """
        homepage_id = self.env['ir.ui.view'].search([
            ('website_id', '=', self.env.ref('website.default_website').id),
            ('key', '=', 'website.homepage'),
        ])
        self.env['ir.ui.view'].create({
            'name': 'Add cache clear to Home',
            'type': 'qweb',
            'mode': 'extension',
            'inherit_id': homepage_id.id,
            'arch_db': """
                <t t-call="website.layout" position="before">
                    <t t-esc="website.env['ir.http']._clear_routing_map()"/>
                </t>
            """,
        })

        r = self.url_open('/')
        r.raise_for_status()
