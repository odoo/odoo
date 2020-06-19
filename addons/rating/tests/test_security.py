# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.tests import tagged, common, new_test_user
from odoo.tools import mute_logger

from functools import partial

rating_new_test_user = partial(new_test_user, context={'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'mail_notrack': True, 'no_reset_password': True})


@tagged('security')
class TestAccessRating(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccessRating, cls).setUpClass()

        cls.user_manager_partner = rating_new_test_user(
            cls.env, name='Jean Admin', login='user_mana', email='admin@example.com',
            groups='base.group_partner_manager,base.group_system'
        )

        cls.user_emp = rating_new_test_user(
            cls.env, name='Eglantine Employee', login='user_emp', email='employee@example.com',
            groups='base.group_user'
        )

        cls.user_portal = rating_new_test_user(
            cls.env, name='Patrick Portal', login='user_portal', email='portal@example.com',
            groups='base.group_portal'
        )

        cls.user_public = rating_new_test_user(
            cls.env, name='Pauline Public', login='user_public', email='public@example.com',
            groups='base.group_public'
        )

        cls.partner_to_rate = cls.env['res.partner'].with_user(cls.user_manager_partner).create({
            "name": "Partner to Rate :("
        })


    @mute_logger('odoo.addons.base.models.ir_model')
    def test_rating_access(self):
        """ Security test : only a employee (user group) can create and write rating object """
        # Public and portal user can't Access direclty to the ratings
        with self.assertRaises(AccessError):
            self.env['rating.rating'].with_user(self.user_portal).create({
                'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'res.partner')], limit=1).id,
                'res_model': 'res.partner',
                'res_id': self.partner_to_rate.id,
                'rating': 1
            })
        with self.assertRaises(AccessError):
            self.env['rating.rating'].with_user(self.user_public).create({
                'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'res.partner')], limit=1).id,
                'res_model': 'res.partner',
                'res_id': self.partner_to_rate.id,
                'rating': 3
            })

        # No error with employee
        ratting = self.env['rating.rating'].with_user(self.user_emp).create({
            'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'res.partner')], limit=1).id,
            'res_model': 'res.partner',
            'res_id': self.partner_to_rate.id,
            'rating': 3
        })

        with self.assertRaises(AccessError):
            ratting.with_user(self.user_portal).write({
                'feedback': 'You should not pass!'
            })
        with self.assertRaises(AccessError):
            ratting.with_user(self.user_public).write({ 
                'feedback': 'You should not pass!'
            })
