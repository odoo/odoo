# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import BaseCase


@tagged('phone_validation')
class TestPhonenumbers(BaseCase):

    def test_country_code_falsy(self):
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

    def test_get_region_data_for_number(self):
        for source, (exp_code, exp_national_number, exp_phone_code) in zip(
            [
                '+32456998877',  # all hail Philippe
                '+1-613-555-0177',  # canada, same phone_code as US
                '+1-202-555-0124',  # us, same phone_code as CA
            ],
            [
                ('BE', '456998877', '32'),
                ('CA', '6135550177', '1'),
                ('US', '2025550124', '1'),
            ],
        ):
            with self.subTest(source=source):
                self.assertDictEqual(
                    phone_validation.phone_get_region_data_for_number(source),
                    {
                        'code': exp_code,
                        'national_number': exp_national_number,
                        'phone_code': exp_phone_code,
                    }
                )

    def test_phone_format_e164_brazil(self):
        """ In the new brazilian phone numbers system, phone numbers add a '9'
            in front of the last 8 digits of mobile numbers.
            Phonenumbers metadata is patched in odoo, however, when E164 is selected,
            phone numbers aren't formatted, thus patched metadata not being applied.
            See format_number in phonenumbers "Early exit for E164 case"
        """
        for number, expected_number in [
            ('11 6123 4560', '+5511961234560'),  # mobile number, must have 9 added
            ('+55 11 6123 4561', '+5511961234561'),  # mobile number, must have 9 added
            ('11 2345 6789', '+551123456789'),  # landline, must NOT have 9 added
            ('+55 11 2345 6798', '+551123456798'),  # landline, must NOT have 9 added
        ]:
            res = phone_validation.phone_format(number, 'BR', '55', force_format='E164')
            self.assertEqual(res, expected_number)
