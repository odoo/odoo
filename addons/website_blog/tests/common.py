# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestWebsiteBlogCommon(common.TransactionCase):
    def setUp(self):
        super(TestWebsiteBlogCommon, self).setUp()

        Users = self.env['res.users']

        group_blog_manager_id = self.ref('website.group_website_designer')
        group_employee_id = self.ref('base.group_user')
        group_public_id = self.ref('base.group_public')

        self.user_employee = Users.with_context({'no_reset_password': True}).create({
            'name': 'Armande Employee',
            'login': 'armande',
            'email': 'armande.employee@example.com',
            'notify_email': 'none',
            'groups_id': [(6, 0, [group_employee_id])]
        })
        self.user_blogmanager = Users.with_context({'no_reset_password': True}).create({
            'name': 'Bastien BlogManager',
            'login': 'bastien',
            'email': 'bastien.blogmanager@example.com',
            'notify_email': 'none',
            'groups_id': [(6, 0, [group_blog_manager_id, group_employee_id])]
        })
        self.user_public = Users.with_context({'no_reset_password': True}).create({
            'name': 'Cedric Public',
            'login': 'cedric',
            'email': 'cedric.public@example.com',
            'notify_email': 'none',
            'groups_id': [(6, 0, [group_public_id])]
        })
