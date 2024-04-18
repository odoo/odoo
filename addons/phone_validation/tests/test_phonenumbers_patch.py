# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

try:
    import phonenumbers
except ImportError:
    phonenumbers = None

from odoo.tests.common import BaseCase
from odoo.tools.parse_version import parse_version
from odoo.addons.phone_validation.lib import phonenumbers_patch

class TestPhonenumbersPatch(BaseCase):

    def _assert_region_numbers_validity(self, region_code: str, numbers: list):
        """Helper function checking validity of all given phone numbers for a given region.
            :param str region_code: The region code, e.g., 'MA' for Morocco.
            :param list numbers: A list of strings representing phone numbers that should be valid."""
        if not phonenumbers:
            self.skipTest(f'Cannot test "{region_code}" numbers validity without phonenumbers module installed.')

        for phone in numbers:
            phone_obj = phonenumbers.parse(phone, region=region_code, keep_raw_input=True)
            self.assertTrue(phonenumbers.is_valid_number(phone_obj),
                f'The number {phone} is not valid (should be) for region "{region_code}"')


    def test_region_CI_monkey_patch(self):
        """Test if the  patch is apply on the good version of the lib
        And test some phonenumbers"""
        if not phonenumbers:
            self.skipTest('Cannot test without phonenumbers module installed.')
        # MONKEY PATCHING phonemetadata of Ivory Coast if phonenumbers is too old
        if not parse_version('7.6.1') <= parse_version(phonenumbers.__version__) < parse_version('8.12.32'):
            self.assertNotEqual(
                phonenumbers.PhoneMetadata._region_available['CI'],
                phonenumbers_patch._local_load_region,
                "The code should not be monkey patched with phonenumbers > 8.12.32.",
            )
        # check that you can load a new ivory coast phone number without error
        parsed_phonenumber_1 = phonenumbers.parse("20 25/35-51 ", region="CI", keep_raw_input=True)
        self.assertEqual(parsed_phonenumber_1.national_number, 20253551, "The national part of the phonenumber should be 22522586")
        self.assertEqual(parsed_phonenumber_1.country_code, 225, "The country code of Ivory Coast is 225")

        parsed_phonenumber_2 = phonenumbers.parse("+225 22 52 25 86 ", region="CI", keep_raw_input=True)
        self.assertEqual(parsed_phonenumber_2.national_number, 22522586, "The national part of the phonenumber should be 22522586")
        self.assertEqual(parsed_phonenumber_2.country_code, 225, "The country code of Ivory Coast is 225")

    def test_region_MU_monkey_patch(self):
        """Makes sure that patch for Mauritius phone numbers work"""
        if not phonenumbers:
            self.skipTest('Cannot test without phonenumbers module installed.')

        # check that _local_load_region is set to `odoo.addons.phone_validation.lib.phonenumbers_patch._local_load_region`
        # check that you can load a new Mauritius phone number without error
        for test_number, country_region, exp_national_number, exp_country_code in [
            (
                "+23057654321", "", 57654321, 230,
            ), (
                "+2305 76/54 3-21 ", "", 57654321, 230,
            ), (
                "57654321", "MU", 57654321, 230,
            ), (
                "5 76/54 3-21 ", "MU", 57654321, 230,
            ),
        ]:
            with self.subTest(exp_national_number=exp_national_number, exp_country_code=exp_country_code):
                parsed_phonenumber = phonenumbers.parse(test_number, region=country_region, keep_raw_input=True)
                self.assertTrue(phonenumbers.is_valid_number(parsed_phonenumber))
                self.assertEqual(parsed_phonenumber.national_number, exp_national_number)
                self.assertEqual(parsed_phonenumber.country_code, exp_country_code)

    def test_region_PA_monkey_patch(self):
        """Makes sure that patch for Panama's phone numbers work"""
        if not phonenumbers:
            self.skipTest('Cannot test without phonenumbers module installed.')
        # MONKEY PATCHING phonemetadata of Panama if phonenumbers is too old
        if parse_version(phonenumbers.__version__) >= parse_version('8.12.43'):
            self.assertNotEqual(
                phonenumbers.PhoneMetadata._region_available['PA'],
                phonenumbers_patch._local_load_region,
                "The phonenumbers module should not get patched after version 8.12.43",
            )
        # Mobile phone number without country code
        parsed = phonenumbers.parse('6198 5462', region='PA')
        self.assertTrue(phonenumbers.is_valid_number(parsed))
        self.assertEqual(parsed.country_code, 507)
        # Landline phone number with country code
        parsed = phonenumbers.parse('+507 833 8744')
        self.assertTrue(phonenumbers.is_valid_number(parsed))
        self.assertEqual(parsed.national_number, 8338744)

    def test_region_SN_monkey_patch(self):
        """Makes sure that patch for Senegalese phone numbers work"""
        version_to_patch_up_to = '8.12.29'
        region_code='SN'
        correct_SN_numbers = [
            '+221750142092',
            '+22176 707 0065'
        ]
        self._assert_region_numbers_validity(region_code, numbers=correct_SN_numbers)

        if not parse_version(phonenumbers.__version__) < parse_version(version_to_patch_up_to):
            self.assertNotEqual(phonenumbers.PhoneMetadata._region_available[region_code], phonenumbers_patch._local_load_region,
                f'The phonenumbers module should not get patched after version {version_to_patch_up_to}')
