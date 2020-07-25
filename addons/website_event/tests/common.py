# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event.tests.common import TestEventCommon


class TestWebsiteEventCommon(TestEventCommon):

    def _get_menus(self):
        return set(['Introduction', 'Location', 'Register'])

    def _assert_website_menus(self, event):
        self.assertTrue(event.menu_id)

        menus = self.env['website.menu'].search([('parent_id', '=', event.menu_id.id)])
        self.assertEqual(len(menus), len(self._get_menus()))
        self.assertEqual(set(menus.mapped('name')), self._get_menus())
