# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestPosPhoneSearch(TransactionCase):

    def test_phone_search_minimum_length(self):
        Partner = self.env['res.partner']
        for minimum in (3, 4):
            with self.subTest(minimum=minimum), patch.object(self.env.registry['res.partner'], '_phone_search_min_length', minimum):
                with self.assertRaisesRegex(UserError, f'Please enter at least {minimum} characters'):
                    Partner.search([('phone_mobile_search', 'ilike', '1' * (minimum - 1))])

    def test_phone_search_formatted_numbers(self):
        Partner = self.env['res.partner']
        partner = Partner.create({'name': "Phone search customer", 'phone': '+32 485 11 22 33'})
        other_partner = Partner.create({'name': "Other customer", 'mobile': '0032 485 11 22 33'})
        for query in ('485', '+32485', '0032485'):
            with self.subTest(query=query):
                result = Partner.search([('phone_mobile_search', 'ilike', query)])
                self.assertIn(partner, result)
                self.assertIn(other_partner, result)
