# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(TransactionCase):

    def test_validate_fiscal_code(self):
        valid_codes = [
            "AORTHV05P30V295L",
            "SPDTHB43S93F42VH",
            "MDRTUV99H14X2MNU",
            "XPTDRX73R64YPLUD",
            "LOLXDR40T3MZRTSV",
            "GJTIUG55DLQZRTSS",
            "CDEOTG5PBLQZRTSE",
            "PERTLELPALQZRTSN",
            "IT12345678887",
            "IT12345670546",
            "IT95286931217",
            "IT95867361206",
            "IT94567689990",
            "12345670546",
            "95286931217",
            "95867361206",
            "94567689990",
        ]

        invalid_codes = [
            "AORTHV05P34V295U",
            "SPDTHB43O93F42VH",
            "MDRTUVV9H14X2MNU",
            "XPTDRX73RS4YPLUD",
            "LOLXDRQ0T3QZRTSJ",
            "GJTIUGR5DLQZRTSS",
            "CDEOTG5PBLQZRTSS",
            "PERTLEZPALQZRTSN",
            "IT12345678901",
            "IT12345678885",
            "IT45689349992",
            "IT78239131204",
            "IT45692151219",
            "12345678901",
            "12345678885",
            "45689349992",
            "78239131204",
            "45692151219",
        ]

        partners = self.env['res.partner']

        for i, code in enumerate(invalid_codes):
            with self.assertRaises(UserError):
                partners += self.env['res.partner'].create({'name': f'partner_{i}', 'l10n_it_codice_fiscale': code})

        for i, code in enumerate(valid_codes):
            partners += self.env['res.partner'].create({'name': f'partner_{i}', 'l10n_it_codice_fiscale': code})

        self.assertEqual(len(partners), len(valid_codes))

    def test_partner_l10n_it_codice_fiscale(self):
        vat_partner = self.env['res.partner'].create({
            'name': 'Customer with VAT',
        })

        partner_form = Form(vat_partner)

        partner_form.vat = 'IT12345676017'
        self.assertEqual(partner_form.l10n_it_codice_fiscale, '12345676017', "We give the Parnter a VAT, l10n_it_codice_fiscale is given accordingly")

        partner_form.country_id = self.env.ref('base.ir')
        self.assertFalse(partner_form.l10n_it_codice_fiscale, "Partner is given Iran as country, l10n_it_codice_fiscale is removed")

        partner_form.country_id = self.env.ref('base.it')
        self.assertEqual(partner_form.l10n_it_codice_fiscale, '12345676017', "The partner was given the wrong country, we correct it to Italy")

        partner_form.vat = 'IT12345670017'
        self.assertEqual(partner_form.l10n_it_codice_fiscale, '12345670017', "There was a typo in the VAT, changing it should change l10n_it_codice_fiscale as well")
