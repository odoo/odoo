# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import re


class ResPartner(models.Model):
    _inherit = "res.partner"
    _rec_names_search = ["display_name", "email", "ref", "vat", "company_registry", "l10n_hu_vat_group_number"]

    l10n_hu_is_vat_group_member = fields.Boolean(
        "TAX Group membership", default=False, help="If the company is a member of a vat group.", index=True
    )
    l10n_hu_vat_group_number = fields.Char(
        "TAX Group Number",
        size=13,
        copy=False,
        help="TAX Group Number, if this company is a member of a Hungarian TAX group",
        index=True,
    )

    l10n_hu_company_tax_arrangments = fields.Selection(
        [
            ("ie", "Individual Exemption"),
            ("ca", "Cash Accounting"),
            ("sb", "Small Business"),
        ],
        string="Special tax arrangements",
    )

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + [
            "l10n_hu_is_vat_group_member",
            "l10n_hu_vat_group_number",
            "l10n_hu_company_tax_arrangments",
        ]

    __check_vat_hu_companies_eu_re = re.compile(r"^HU(\d{7})(\d)$")
    __check_vat_hu_companies_re = re.compile(
        r"^(\d{7})(\d)(?P<optional_1>-)?([1-5])(?P<optional_2>-)?(0[2-9]|[13][0-9]|2[02-9]|4[0-4]|51)$"
    )
    __check_vat_hu_individual_re = re.compile(r"^8\d{9}$")

    def check_vat_hu(self, vat):
        # Hungarian tax number verification - offline method
        # The tax number consists of 11 digits. The eighth digit is the control number.
        # The control number is generated as follows:
        # The first seven digits are multiplied by the digits 9, 7, 3, 1, 9, 7, 3 in descending order of their local
        # value, the multiplications are added together and the number at the local value of 1 in the result is
        # subtracted from 10. The difference is the control number.

        # 8xxxxxxxxy, Tin number for individual, it has to start with an 8 and finish with the check digit

        # Magyar adószám ellenőrzése - offline módszer
        # Az adószám 11 számjegyből áll. A nyolcadik számjegye az ellenőrző szám.
        # Az ellenőrző szám képzése az alábbiak szerint történik:
        # Az első hét számjegyet helyiértékük csökkenő sorrendjében szorozzuk a 9, 7, 3, 1, 9, 7, 3 számjegyekkel,
        # a szorzatokat összeadjuk, és az eredmény 1-es helyiértékén lévő számot kivonjuk 10-ből. A különbség
        # az ellenőrző szám.

        # Another: https://prog.hu/tudastar/180161/javascript-adoszam-regex

        if vat and vat.startswith("HU"):
            # HU12345678
            vat_regex = self.__check_vat_hu_companies_eu_re

        # positive individual match
        elif self.__check_vat_hu_individual_re.match(vat):
            return True

        else:
            # 12345678-1-12
            # 12345678112
            vat_regex = self.__check_vat_hu_companies_re

        matches = re.fullmatch(vat_regex, vat)
        if not matches:
            return False

        identifier_number, check_digit, *_ = matches.groups()

        multipliers = [9, 7, 3, 1, 9, 7, 3]
        checksum_digit = sum(map(lambda n, m: int(n) * m, identifier_number, multipliers)) % 10
        if checksum_digit > 0:
            checksum_digit = 10 - checksum_digit

        return int(check_digit) == checksum_digit

    @api.model
    def _run_vies_test(self, vat_number, default_country):
        """Convert back the hungarian format to EU format: 12345678-1-12 => HU12345678"""
        if default_country and default_country.code == "HU" and not vat_number.startswith("HU"):
            vat_number = f"HU{vat_number[:8]}"
        return super()._run_vies_test(vat_number, default_country)
