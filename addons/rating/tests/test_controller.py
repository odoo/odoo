# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import HttpCase, tagged, new_test_user

@tagged('post_install', '-at_install')
class TestControllersRoute(HttpCase):

    def setUp(self):
        super(TestControllersRoute, self).setUp()
        self.user = new_test_user(self.env, "test_user_1", email="test_user_1@nowhere.com", tz="UTC")
        self.partner = self.user.partner_id

    def test_controller_rating(self):

        rating_test = self.env['rating.rating'].with_user(self.user).create({
            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'res.partner')], limit=1).id,
            'res_model': 'res.partner',
            'res_id': self.partner.id,
            'rating': 3
        })
        self.authenticate(None, None)
        access_token = rating_test.access_token
        url = '/rate/%s/submit_feedback' % access_token
        req = self.url_open(url)
        self.assertEqual(req.status_code, 200, "Response should = OK")

    def test_controller_rating_multi_company(self):
        extra_company = self.env["res.company"].create({"name": "Extra company"})
        partner = self.env["res.partner"].create({
            "name": "Test partner",
            "company_id": extra_company.id,
        })
        rating_test = self.env['rating.rating'].with_user(self.user).create({
            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'res.partner')], limit=1).id,
            'res_model': 'res.partner',
            'res_id': partner.id,
            'rating': 3
        })
        self.authenticate(None, None)
        access_token = rating_test.access_token
        url = '/rate/%s/submit_feedback' % access_token
        req = self.url_open(url)
        self.assertIn("Extra company", str(req.content))
