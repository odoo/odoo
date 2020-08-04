# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event.tests.common import TestEventCommon
from odoo.addons.mail.tests.common import mail_new_test_user


class TestWebsiteEventCommon(TestEventCommon):

    @classmethod
    def setUpClass(cls):
        super(TestWebsiteEventCommon, cls).setUpClass()

        cls.company_main = cls.env.user.company_id
        cls.user_event_web_manager = mail_new_test_user(
            cls.env, login='user_event_web_manager',
            name='Martin Sales Manager', email='crm_manager@test.example.com',
            company_id=cls.company_main.id,
            notification_type='inbox',
            groups='event.group_event_manager,website.group_website_designer',
        )

    def _get_menus(self):
        return set(['Introduction', 'Location', 'Register'])

    def _assert_website_menus(self, event, menu_entries=None):
        self.assertTrue(event.menu_id)

        if menu_entries is None:
            menu_entries = self._get_menus()

        menus = self.env['website.menu'].search([('parent_id', '=', event.menu_id.id)])
        self.assertEqual(len(menus), len(menu_entries))
        self.assertEqual(set(menus.mapped('name')), menu_entries)

        for page_specific in ['Introduction', 'Location']:
            view = self.env['ir.ui.view'].search(
                [('name', '=', page_specific + ' ' + event.name)]
            )
            if page_specific in menu_entries:
                self.assertTrue(bool(view))
            # TDE FIXME: page deletion not done in 13.3 for Introduction/Location, difficult to fix
            # without website.event.menu model (or crappy code based on name)
            # else:
            #     self.assertFalse(bool(view))
