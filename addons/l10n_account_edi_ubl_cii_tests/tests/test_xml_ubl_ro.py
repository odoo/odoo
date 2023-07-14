# -*- coding: utf-8 -*-

import base64

from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.tests import tagged
from odoo.tools.misc import file_open
from lxml import etree, isoschematron
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
            'city': 'Bucharest',
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
            'city': "Bucharest",
            'zip': "010101",
            'vat': 'RO1234567897',
            'phone': '+40 123 456 789',
            'street': "Strada Kunst, 3",
            'country_id': cls.env.ref('base.ro').id,
            'ref': 'ref_partner_a',
            'ubl_cii_format': 'ciusro' # should be selected automatically! (?)
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

    def test_anaf(self, attachment=None, manual_check=False):
        if not attachment:
            return
        xml_content = base64.b64decode(attachment.with_context(bin_size=False).datas)
        if manual_check:
            from pathlib import Path
            with Path("~/work/odoo/.notes/test.xml").expanduser().open("wb") as f:
                f.write(xml_content)
                print("wrote to test.xml")

        url = 'https://webservicesp.anaf.ro/prod/FCTEL/rest/validare/FACT1'
        headers = {'Content-Type': 'text/plain'}
        response = requests.post(url, data=xml_content, headers=headers)
        json = response.json()
        print("=====================================================")
        print("\n")

        for message_obj in json['Messages']:
            message = message_obj['message']
            print(message, "\n\n")
        print("=====================================================")

    ####################################################
    # Test export - import
    ####################################################

    def test_export_invoice_ro(self):
        invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
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
        attachment = invoice.ubl_cii_xml_id
        self.assertTrue(attachment)
        self.test_anaf(attachment)
        self.assertEqual(attachment.name[-11:], "cius_ro.xml")
