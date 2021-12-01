# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestWebsiteBlogCommon(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        Users = cls.env['res.users']

        group_blog_manager_id = cls.env.ref('website.group_website_designer').id
        group_employee_id = cls.env.ref('base.group_user').id
        group_public_id = cls.env.ref('base.group_public').id

        cls.user_employee = Users.with_context({'no_reset_password': True}).create({
            'name': 'Armande Employee',
            'login': 'armande',
            'email': 'armande.employee@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [group_employee_id])]
        })
        cls.user_blogmanager = Users.with_context({'no_reset_password': True}).create({
            'name': 'Bastien BlogManager',
            'login': 'bastien',
            'email': 'bastien.blogmanager@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [group_blog_manager_id, group_employee_id])]
        })
        cls.user_public = Users.with_context({'no_reset_password': True}).create({
            'name': 'Cedric Public',
            'login': 'cedric',
            'email': 'cedric.public@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [group_public_id])]
        })

        cls.test_blog = cls.env['blog.blog'].with_user(cls.user_blogmanager).create({
            'name': 'New Blog',
        })
        cls.test_blog_post = cls.env['blog.post'].with_user(cls.user_blogmanager).create({
            'name': 'New Post',
            'blog_id': cls.test_blog.id,
            'website_published': True,
        })
