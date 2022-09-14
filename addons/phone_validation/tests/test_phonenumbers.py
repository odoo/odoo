# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.phone_validation.tools import phone_validation
from odoo.tests import tagged
from odoo.tests.common import BaseCase


@tagged('phone_validation')
class TestPhonenumbers(BaseCase):

    def test_country_code_falsy(self):
        print(phone_validation.phone_parse('0456998877', None))
        print(phone_validation.phone_parse('0456998877', False))
        self.assertEqual(
            phone_validation.phone_format('0456998877', 'BE', '32', force_format='E164'),
            '+32456998877'
        )
        self.assertEqual(
            phone_validation.phone_format('0456998877', None, '32', force_format='E164'),
            '+32456998877'
        )
