# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .sign_request_common import SignRequestCommon

from odoo import Command

from odoo.addons.mail.tests.common import MockEmail
from odoo.tests import tagged


@tagged('multi_company')
class TestSignMulticompany(SignRequestCommon, MockEmail):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_2 = cls.env['res.company'].create({'name': 'Company2'})
        cls.company_3 = cls.env['res.company'].create({'name': 'Company3'})

    def test_sign_request_multicompany_refuse(self):
        with self.mock_mail_gateway():
            sign_request = self.env['sign.request'].with_company(self.company_2).create({
                'template_id': self.template_1_role.id,
                'reference': self.template_1_role.display_name,
                'request_item_ids': [Command.create({
                    'partner_id': self.partner_1.id,
                    'role_id': self.env.ref('sign.sign_item_role_customer').id,
                })],
            })
            # Original mail should contain reference to company_2
            self.assertSentEmail('"OdooBot" <odoobot@example.com>', self.partner_1, body_content='Company2')

            # Followup mail should contain reference to company_2
            sign_request.request_item_ids.with_company(self.company_3)._refuse('')
            self.assertSentEmail('"OdooBot" <odoobot@example.com>', self.partner_1, body_content='Company2')

    def test_sign_request_multicompany_sign(self):
        with self.mock_mail_gateway():
            sign_request = self.env['sign.request'].with_company(self.company_2).create({
                'template_id': self.template_1_role.id,
                'reference': self.template_1_role.display_name,
                'request_item_ids': [Command.create({
                    'partner_id': self.partner_1.id,
                    'role_id': self.env.ref('sign.sign_item_role_customer').id,
                })],
            })
            # Original mail should contain reference to company_2
            self.assertSentEmail('"OdooBot" <odoobot@example.com>', self.partner_1, body_content='Company2')

            # Followup mail should contain reference to company_2
            sign_request.request_item_ids.with_company(self.company_3)._edit_and_sign(self.single_role_customer_sign_values)
            self.assertSentEmail('"OdooBot" <odoobot@example.com>', self.partner_1, body_content='Company2')
