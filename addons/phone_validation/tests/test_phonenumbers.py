# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

try:
    import phonenumbers
except ImportError:
    phonenumbers = None

from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import BaseCase


@tagged('phone_validation')
class TestPhonenumbers(BaseCase):

    def test_country_code_falsy(self):
        if not phonenumbers:
            self.skipTest('Cannot test without phonenumbers module installed.')

        self.assertEqual(
            phone_validation.phone_format('0456998877', 'BE', '32', force_format='E164'),
            '+32456998877'
        )
        # no country code -> UserError, no internal traceback
        with self.assertRaises(UserError):
            self.assertEqual(
                phone_validation.phone_format('0456998877', None, '32', force_format='E164'),
                '+32456998877'
            )
