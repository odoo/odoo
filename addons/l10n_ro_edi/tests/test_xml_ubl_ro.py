# -*- coding: utf-8 -*-

import base64
from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.tests import tagged
from odoo import Command
import requests


# TODO - remove 'yoni' tag when done
@tagged('post_install_l10n', 'post_install', '-at_install', 'yoni')
class TestUBLRO(TestUBLCommon, TestAccountMoveSendCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="ro"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.ro').id,
            'currency_id': cls.env.ref('base.RON').id,
            'state_id': cls.env.ref('base.RO_B').id,
            'city': 'SECTOR1',
            'zip': '010101',
            'vat': 'RO1234567897',
            'phone': '+40 123 456 789',
            'street': "Strada Kunst, 3",
            'invoice_is_ubl_cii': True,
        })
        cls.env['res.partner.bank'].create({
            'acc_type': 'iban',
            'partner_id': cls.company_data['company'].partner_id.id,
            'acc_number': 'RO98RNCB1234567890123456',
        })

        cls.partner_a = cls.env['res.partner'].create({
            'name': "Roasted Romanian Roller",
            'city': "SECTOR3",
            'zip': "010101",
            'vat': 'RO1234567897',
            'phone': '+40 123 456 780',
            'street': "Rolling Roast, 88",
            'country_id': cls.env.ref('base.ro').id,
            'state_id': cls.env.ref('base.RO_B').id,
            'ref': 'ref_partner_a',
        })

        cls.partner_b = cls.env['res.partner'].create({
            'name': "Belgian Bean Burrito",
            'city': "Brussels",
            'zip': "1000",
            'vat': 'BE0477472701',
            'phone': '+32 123 456 789',
            'street': "Rue de la Madeleine, 1",
            'country_id': cls.env.ref('base.be').id,
            'ref': 'ref_partner_b',
            'ubl_cii_format': 'ciusro'
        })

        cls.tax_19 = cls.env['account.tax'].create({
            'name': 'tax_19',
            'amount_type': 'percent',
            'amount': 19,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.ro').id,
        })

    ####################################################
    # Helper method - remove when done! -TODO-
    ####################################################
    def create_invoice_attachment(self, partner_id=False):
        if not partner_id:
            return
        invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': partner_id,
            'partner_bank_id': self.env.company.partner_id.bank_ids[:1].id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'narration': 'test narration',
            'ref': 'ref_move',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'quantity': 2.0,
                    'price_unit': 350.0,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
            ],
        })
        invoice.action_post()
        invoice._generate_pdf_and_send_invoice(self.move_template)
        return invoice.ubl_cii_xml_id

    @staticmethod
    def post_anaf(attachment=None, manual_check=False):
        if not attachment:
            return
        xml_content = base64.b64decode(attachment.with_context(bin_size=False).datas)
        if manual_check:
            from pathlib import Path
            with Path("/.notes/test.xml").expanduser().open("wb") as f:
                f.write(xml_content)
                print("wrote to test.xml")
        url = 'https://webservicesp.anaf.ro/prod/FCTEL/rest/validare/FACT1'
        headers = {'Content-Type': 'text/plain'}
        response = requests.post(url, data=xml_content, headers=headers)
        json = response.json()
        print("=====================================================\n\n")
        if 'Messages' in json:
            for message_obj in json['Messages']:
                message = message_obj['message']
                print(message, "\n\n")
        else:
            print(json, '\n\n')
        print("=====================================================")

    ####################################################
    # Test export - import
    ####################################################

    # def test_export_invoice_ro_domestic(self):
    #     invoice = self.env["account.move"].create({
    #         'move_type': 'out_invoice',
    #         'partner_id': self.partner_a.id,
    #         'partner_bank_id': self.env.company.partner_id.bank_ids[:1].id,
    #         'invoice_payment_term_id': self.pay_terms_b.id,
    #         'invoice_date': '2017-01-01',
    #         'date': '2017-01-01',
    #         'narration': 'test narration',
    #         'ref': 'ref_move',
    #         'invoice_line_ids': [
    #             Command.create({
    #                 'product_id': self.product_a.id,
    #                 'quantity': 1.0,
    #                 'price_unit': 500.0,
    #                 'tax_ids': [(6, 0, self.tax_19.ids)],
    #             }),
    #             Command.create({
    #                 'product_id': self.product_b.id,
    #                 'quantity': 2.0,
    #                 'price_unit': 350.0,
    #                 'tax_ids': [(6, 0, self.tax_19.ids)],
    #             }),
    #         ],
    #     })
    #     invoice.action_post()
    #     invoice._generate_pdf_and_send_invoice(self.move_template)
    #     attachment = invoice.ubl_cii_xml_id
    #     self.assertTrue(attachment)
    #     self.post_anaf(attachment)
    #     self.assertEqual(attachment.name[-11:], "cius_ro.xml")

    # def test_change_company_value_here(self):
    #     self.company_data["company"].write({ "city": "NEWSECTOR"})
    #     print(self.company_data["company"]["city"], "\n\n")

    # def test_detect_change_company_value(self):
    #     print("\n\nDETECTING COMPANY VALUE:")
    #     print(self.company_data["company"]["city"], "\n\n")

    # TODO check all rules from schematron
    # Checked Rules:
    # 020 001 A020 010
    # Notes:
    # string-length constrains are skipped

    """
    (normalize-space(cbc:TaxCurrencyCode) = 'RON' and normalize-space(cbc:DocumentCurrencyCode) != 'RON') or 
    (normalize-space(cbc:TaxCurrencyCode) = 'RON' and normalize-space(cbc:DocumentCurrencyCode) = 'RON')  or 
    (normalize-space(cbc:TaxCurrencyCode) != 'RON' and normalize-space(cbc:DocumentCurrencyCode) = 'RON') or 
    (not(exists (cbc:TaxCurrencyCode)) and normalize-space(cbc:DocumentCurrencyCode) = 'RON')
    # If the Invoice currency code (BT-5) is other than RON, then the VAT accounting currency code(BT-6) must be RON.
    """
    def test_diff_currency_code(self):
        self.company_data["company"].write({
            "currency_id": self.env.ref("base.AUD").id,
        })
        attachment = self.create_invoice_attachment(self.partner_a.id)
        self.post_anaf(attachment, True)
