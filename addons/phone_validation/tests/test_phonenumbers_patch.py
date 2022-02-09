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
    def test_region_CI_monkey_patch(self):
        """Test if the  patch is apply on the good version of the lib
        And test some phonenumbers"""
        if not phonenumbers:
            self.skipTest('Cannot test without phonenumbers module installed.')
        # MONKEY PATCHING phonemetadata of Ivory Coast if phonenumbers is too old
        if parse_version('7.6.1') <= parse_version(phonenumbers.__version__) < parse_version('8.12.32'):
            # check that _local_load_region is set to `odoo.addons.phone_validation.lib.phonenumbers_patch._local_load_region`
            # check that you can load a new ivory coast phone number without error
            parsed_phonenumber_1 = phonenumbers.parse("20 25/35-51 ", region="CI", keep_raw_input=True)
            self.assertEqual(parsed_phonenumber_1.national_number, 20253551, "The national part of the phonenumber should be 22522586")
            self.assertEqual(parsed_phonenumber_1.country_code, 225, "The country code of Ivory Coast is 225")

            parsed_phonenumber_2 = phonenumbers.parse("+225 22 52 25 86 ", region="CI", keep_raw_input=True)
            self.assertEqual(parsed_phonenumber_2.national_number, 22522586, "The national part of the phonenumber should be 22522586")
            self.assertEqual(parsed_phonenumber_2.country_code, 225, "The country code of Ivory Coast is 225")
        else:
            self.assertFalse(hasattr(phonenumbers_patch, '_local_load_region'),
                "The code should not be monkey patched with phonenumbers > 8.12.32.")
