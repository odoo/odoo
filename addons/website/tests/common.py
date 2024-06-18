# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import HttpCase


class HttpCaseWithUserEditor(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_admin = cls.env.ref('base.user_admin')
        cls.user_admin.write({'name': 'Mitchell Admin'})
        cls.partner_admin = cls.user_admin.partner_id
        cls.user_editor = cls.env['res.users'].search([('login', '=', 'editor')])
        cls.partner_editor = cls.user_editor.partner_id

        if not cls.user_editor:
            cls.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 6)
            cls.partner_editor = cls.env['res.partner'].create({
                'name': 'Peter Editor',
                'email': 'peter.editor@example.com',
            })
            cls.user_editor = cls.env['res.users'].create({
                'login': 'editor',
                'password': 'editor',
                'partner_id': cls.partner_editor.id,
                'groups_id': [Command.set([cls.env.ref('base.group_user').id, cls.env.ref('website.group_website_restricted_editor').id])],
            })
