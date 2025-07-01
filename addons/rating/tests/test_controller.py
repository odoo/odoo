# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import HttpCase, tagged, new_test_user
from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal

@tagged('post_install', '-at_install')
class TestControllersRoute(HttpCaseWithUserDemo, HttpCaseWithUserPortal):

    def setUp(self):
        super(TestControllersRoute, self).setUp()
        self.user = new_test_user(self.env, "test_user_1", email="test_user_1@nowhere.com", tz="UTC")
        self.partner = self.user.partner_id
        self.rated_partner = self.env['res.partner'].create({
            'name': 'Test company',
            'email': "testcompany@example.com",
            'is_company': True,
            'child_ids': [
                (0, 0, {'name': 'Test child_1', 'type': 'contact', 'email': "testchild_1@example.com",}),
            ]
        })

    def test_controller_rating(self):
        [rating_test_1, rating_test_2, rating_test_3] = self.env['rating.rating'].with_user(self.user).create([{
            'res_model_id': self.env['ir.model']._get_id('res.partner'),
            'res_model': 'res.partner',
            'res_id': self.rated_partner.id,
            'partner_id': self.partner.id,
            'rating': 3
        } for i in range(3)])

        self.authenticate(None, None)
        access_token = rating_test_1.access_token
        url = '/rate/%s/submit_feedback' % access_token
        req = self.url_open(url)
        self.assertEqual(req.status_code, 200, "Response should = OK")

        # changed behavior in Odoo 16+: the GET request to /rate/{access_token}/int
        # will not trigger a consume of the rating. User needs to submit the Form
        details = [
            (self.user_demo.login, rating_test_1, rating_test_1.access_token, False),
            (self.user.login, rating_test_1, rating_test_1.access_token, False),
            (None, rating_test_2, rating_test_2.access_token, False),
            (self.user_portal.login, rating_test_3, rating_test_3.access_token, False)
        ]

        for login, rating_test, access_token, expected_consume in details:
            with self.subTest(login=login, access_token=access_token, rating_test=rating_test, expected_consume=expected_consume):
                if login == self.user_portal.login:
                    rating_test.partner_id = self.rated_partner.child_ids.id
                    self.partner_portal.parent_id = self.rated_partner.id

                self.authenticate(login, login)
                res = self.url_open(f"/rate/{access_token}/5")
                self.assertEqual(res.status_code, 200)
                self.assertEqual(rating_test.consumed, expected_consume)

                message = b'You cannot rate this' if login == self.user_demo.login else b'Feel free to share feedback on your experience:'
                self.assertIn(message, res.content)
