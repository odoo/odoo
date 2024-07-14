# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import product

from odoo.exceptions import UserError
from odoo.addons.whatsapp.tests.common import WhatsAppCommon
from odoo.addons.whatsapp.tools import phone_validation as wa_phone_validation
from odoo.tests import tagged


@tagged('phone_validation')
class PhoneFormat(WhatsAppCommon):

    def test_phone_format(self):
        """ Test various phone format done in whatsapp, as it uses some specific
        custom format tools. """
        us_country = self.env.ref('base.us')
        be_country = self.env.ref('base.be')
        base_record = self.env['res.partner'].create({
            'country_id': be_country.id,
            'name': 'Record for Context',
            })
        test_numbers = [
            "32485221100",  # this is normally what we expect from WA as input
            "0485221100",  # local
            "+32485221100",  # E164
            "+32 485 22 11 00",  # INTL
            "0032485221100",
        ]
        expected = [
            # formats are: E164, INTL, WHATSAPP
            "+32485221100", "+32 485 22 11 00", "32485221100",
            "+32485221100", "+32 485 22 11 00", "32485221100",
            "+32485221100", "+32 485 22 11 00", "32485221100",
            "+32485221100", "+32 485 22 11 00", "32485221100",
            "+32485221100", "+32 485 22 11 00", "32485221100",
        ]
        for (number, force_format), expected in zip(
            product(
                test_numbers,
                ('E164', 'INTERNATIONAL', 'WHATSAPP')
            ), expected):
            with self.subTest(number=number, force_format=force_format):
                formatted = wa_phone_validation.wa_phone_format(
                    base_record,
                    number=number,
                    force_format=force_format,
                )
                self.assertEqual(formatted, expected)

            # local number cannot be formatted with wrong or missing country code
            if number == "0485221100":
                with self.assertRaises(UserError):
                    formatted = wa_phone_validation.wa_phone_format(
                        base_record,
                        number=number,
                        country=us_country,  # force wrong country
                        force_format=force_format,
                    )
                with self.assertRaises(UserError):
                    formatted = wa_phone_validation.wa_phone_format(
                        self.env['res.partner'],  # force no country
                        number=number,
                        force_format=force_format,
                    )
                continue
            # other numbers are complete and ignore wrong or missing country code
            with self.subTest(number=number, force_format=force_format, force_country=us_country):
                formatted = wa_phone_validation.wa_phone_format(
                    base_record,
                    number=number,
                    country=us_country,  # force wrong country
                    force_format=force_format,
                )
                self.assertEqual(formatted, expected)

            with self.subTest(number=number, force_format=force_format, force_country=False):
                formatted = wa_phone_validation.wa_phone_format(
                    self.env['res.partner'],  # force no country
                    number=number,
                    force_format=force_format,
                )
                self.assertEqual(formatted, expected)
