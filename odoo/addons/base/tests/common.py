# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import SavepointCase, TransactionCase, HttpCase


class TransactionCaseWithUserDemo(TransactionCase):

    def setUp(self):
        super(TransactionCaseWithUserDemo, self).setUp()

        self.env.ref('base.partner_admin').write({'name': 'Mitchell Admin'})
        self.user_demo = self.env['res.users'].search([('login', '=', 'demo')])
        self.partner_demo = self.user_demo.partner_id

        if not self.user_demo:
            self.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            # YTI TODO: This could be factorized between the different classes
            self.partner_demo = self.env['res.partner'].create({
                'name': 'Marc Demo',
                'email': 'mark.brown23@example.com',
            })
            self.user_demo = self.env['res.users'].create({
                'login': 'demo',
                'password': 'demo',
                'partner_id': self.partner_demo.id,
                'groups_id': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('base.group_partner_manager').id])],
            })


class HttpCaseWithUserDemo(HttpCase):

    def setUp(self):
        super(HttpCaseWithUserDemo, self).setUp()
        self.env.ref('base.partner_admin').write({'name': 'Mitchell Admin'})
        self.user_demo = self.env['res.users'].search([('login', '=', 'demo')])
        self.partner_demo = self.user_demo.partner_id

        if not self.user_demo:
            self.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            self.partner_demo = self.env['res.partner'].create({
                'name': 'Marc Demo',
                'email': 'mark.brown23@example.com',
            })
            self.user_demo = self.env['res.users'].create({
                'login': 'demo',
                'password': 'demo',
                'partner_id': self.partner_demo.id,
                'groups_id': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('base.group_partner_manager').id])],
            })


class SavepointCaseWithUserDemo(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(SavepointCaseWithUserDemo, cls).setUpClass()

        cls.user_demo = cls.env['res.users'].search([('login', '=', 'demo')])
        cls.partner_demo = cls.user_demo.partner_id

        if not cls.user_demo:
            cls.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            cls.partner_demo = cls.env['res.partner'].create({
                'name': 'Marc Demo',
                'email': 'mark.brown23@example.com',
            })
            cls.user_demo = cls.env['res.users'].create({
                'login': 'demo',
                'password': 'demo',
                'partner_id': cls.partner_demo.id,
                'groups_id': [(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('base.group_partner_manager').id])],
            })


class HttpCaseWithUserPortal(HttpCase):

    def setUp(self):
        super(HttpCaseWithUserPortal, self).setUp()
        self.user_portal = self.env['res.users'].search([('login', '=', 'portal')])
        self.partner_portal = self.user_portal.partner_id

        if not self.user_portal:
            self.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            self.partner_portal = self.env['res.partner'].create({
                'name': 'Joel Willis',
                'email': 'joel.willis63@example.com',
            })
            self.user_portal = self.env['res.users'].with_context(no_reset_password=True).create({
                'login': 'portal',
                'password': 'portal',
                'partner_id': self.partner_portal.id,
                'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
            })
