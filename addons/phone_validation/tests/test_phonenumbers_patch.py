# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import NamedTuple, Iterable
try:
    import phonenumbers
except ImportError:
    phonenumbers = None

from odoo.tests.common import BaseCase
from odoo.tools.parse_version import parse_version
from odoo.addons.phone_validation.lib import phonenumbers_patch

class TestPhonenumbersPatch(BaseCase):

    class PhoneInputOutputLine(NamedTuple):
        """ Datastructure to store data for phone number parsing tests. Consist of single set of:
        - input phone data to be parsed
        - (optionally) ground-truths, i.e expected results

        Input phone data can be one of the following:
            - international phone number like: "+23057654321"
            - national phone number + region code, like: "57654321" + "MU"

        :param number: The input phone number to be parsed.
        :param region: (optional) The two-letter ISO country code, used when parsing national number without country prefix eg. "SN"
        :param gt_national_number: (optional) ground-truth to compare parsed national number with
        :param gt_country_code: (optional) ground-truth to compare country calling code eg. 221
        :param gt_italian_leading_zero: (optional) ground-truth for italian_leading_zero, True if expected to find 1 leading zero after parsing
        :param gt_number_of_leading_zeros: (optional) ground-truth to compare number_of_leading_zeros to code, Set if expected more then one leading zero

                     ┌────────┐
            INPUT ─►│ PARSER ├─► OUTPUT          (EXPECTED ground-truth)
                     └────────┘           compare
             number              number ◄───────► (number)
            (region)              code               (code)

        Placeholders in parenthesis () are optional, why are they optional? The idea is that in the most basic parse check
        we would only parse number and check if it's valid (according to implicit phonenumbers implementation). However, we
        might want to perform additional validation on the parsed number, then we'd use optional expected fields that should
        trigger additional checks.
        """
        number: str
        region: str = ""
        gt_national_number: int = None
        gt_country_code: int = None
        gt_italian_leading_zero: bool = None
        gt_number_of_leading_zeros: int = None

    def _assert_parsing_phonenumbers(self, parse_test_lines: Iterable[PhoneInputOutputLine]):
        """ Iterates over test_lines, performs asserts according to what data each test_line contains.
            Simple cases:
            1. test_line contains only the international number -> check if phonenumbers can parse it
            2. test_line contains national number and country code -> check if phonenumbers can parse it
            Presence of expected data:
            In case test line contains some ground-truth this function will compare parsed data against the ground truths.

        :param parse_test_lines: An iterable consisting of PhoneInputOutputLine
        """
        if not phonenumbers:
            self.skipTest(f'Cannot test parsing without phonenumbers module installed.')

        for parse_test_line in parse_test_lines:
            with self.subTest(**parse_test_line._asdict()):
                parsed_phone = phonenumbers.parse(parse_test_line.number, region=parse_test_line.region)
                self.assertTrue(phonenumbers.is_valid_number(parsed_phone),
                    "Phone number does not match any patterns in the metadata.")
                if parse_test_line.gt_national_number:
                    self.assertEqual(parsed_phone.national_number, parse_test_line.gt_national_number,
                        "Parsed national number differs from expected national number")
                if parse_test_line.gt_country_code:
                    self.assertEqual(parsed_phone.country_code, parse_test_line.gt_country_code,
                        "Parsed country code number differs from expected country code")
                if parse_test_line.gt_italian_leading_zero:
                    self.assertEqual(parsed_phone.italian_leading_zero, parse_test_line.gt_italian_leading_zero,
                        "Parsed country code number differs from expected country code")
                if parse_test_line.gt_number_of_leading_zeros:
                    self.assertEqual(parsed_phone.number_of_leading_zeros, parse_test_line.gt_number_of_leading_zeros,
                        "Parsed country code number differs from expected country code")

    def test_region_BR_monkey_patch(self):
        """ Test Brazil phone numbers patch for added 9 in mobile numbers
        It should not be added for fixed lines numbers"""
        if not phonenumbers:
            self.skipTest('Cannot test without phonenumbers module installed.')

        # Mobile number => 9 should be added
        parsed = phonenumbers.parse('11 6123 4567', region="BR")
        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        self.assertEqual(formatted, '+55 11 96123-4567')

        # Fixed line => 9 should not be added
        parsed = phonenumbers.parse('11 2345 6789', region="BR")
        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        self.assertEqual(formatted, '+55 11 2345-6789')

    def test_region_CI_monkey_patch(self):
        """Makes sure that patch for Ivory Coast phone numbers work"""
        parse_test_lines_CI=(
            self.PhoneInputOutputLine("+2250506007995"),
            self.PhoneInputOutputLine("0506007995", region='CI' ,gt_national_number=506007995, gt_country_code=225, gt_italian_leading_zero=True),
            self.PhoneInputOutputLine("+225 05 20 963 777", gt_national_number=520963777, gt_country_code=225, gt_italian_leading_zero=True),
        )
        self._assert_parsing_phonenumbers(parse_test_lines_CI)

    def test_region_CO_monkey_patch(self):
        """Makes sure that patch for Colombian phone numbers work"""
        parse_test_lines_CO=(
            self.PhoneInputOutputLine("3241234567", "CO"),
            self.PhoneInputOutputLine("+57 324 1234567"),
        )
        self._assert_parsing_phonenumbers(parse_test_lines_CO)

    def test_region_MA_monkey_patch(self):
        """Makes sure that patch for Morocco phone numbers work"""
        parse_test_lines_MU = (
            self.PhoneInputOutputLine("+212 6 23 24 56 28"),
            self.PhoneInputOutputLine("+212603190852"),
            self.PhoneInputOutputLine("+212780137429", region="MA"),
            self.PhoneInputOutputLine("+212546547649", region="MU"),
            self.PhoneInputOutputLine("+212690979618", region="MU"),
        )
        self._assert_parsing_phonenumbers(parse_test_lines_MU)

    def test_region_MU_monkey_patch(self):
        """Makes sure that patch for Mauritius phone numbers work"""
        gt_MU_number = 57654321  # what national number we expect after parsing
        gt_MU_code = 230 # what country code we expect after parsing
        parse_test_lines_MU=(
            self.PhoneInputOutputLine("+23057654321", gt_national_number=gt_MU_number, gt_country_code=gt_MU_code),
            self.PhoneInputOutputLine("+2305 76/54 3-21 ", gt_national_number=gt_MU_number, gt_country_code=gt_MU_code),
            self.PhoneInputOutputLine("57654321", region="MU", gt_national_number=gt_MU_number, gt_country_code=gt_MU_code),
            self.PhoneInputOutputLine("5 76/54 3-21 ", region="MU", gt_national_number=gt_MU_number, gt_country_code=gt_MU_code),
        )
        self._assert_parsing_phonenumbers(parse_test_lines_MU)

    def test_region_PA_monkey_patch(self):
        """Makes sure that patch for Panama's phone numbers work"""
        parse_test_lines_PA=(
            self.PhoneInputOutputLine("6198 5462", "PA", gt_country_code=507),
            self.PhoneInputOutputLine("+507 833 8744", gt_national_number=8338744),
        )
        self._assert_parsing_phonenumbers(parse_test_lines_PA)

    def test_region_SN_monkey_patch(self):
        """Makes sure that patch for Senegalese phone numbers work"""
        parse_test_lines_SN=(
            self.PhoneInputOutputLine("+221750142092"),
            self.PhoneInputOutputLine("+22176 707 0065"),
        )
        self._assert_parsing_phonenumbers(parse_test_lines_SN)
