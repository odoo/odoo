# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .sign_request_common import SignRequestCommon


class TestAccessRight(SignRequestCommon):

    def test_update_item_partner(self):
        self.role_customer.change_authorized = True
        sign_request_3_roles = self.create_sign_request_3_roles(customer=self.partner_1, employee=self.partner_2,
                                                                company=self.partner_3, cc_partners=self.partner_4)
        role2sign_request_item = dict([(sign_request_item.role_id, sign_request_item) for sign_request_item in
                                       sign_request_3_roles.request_item_ids])
        sign_request_item_customer = role2sign_request_item[self.role_customer]
        # We update the item partner with a non-privileged sign user.
        sign_request_item_customer.with_user(self.user_1).partner_id = self.partner_5
        # reassign
        self.assertEqual(sign_request_item_customer.signer_email, "char.aznable.a@example.com", 'email address should be char.aznable.a@example.com')
