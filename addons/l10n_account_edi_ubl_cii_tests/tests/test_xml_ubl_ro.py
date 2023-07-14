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
        cls.currency = cls.env["res.currency"].search([("name", "=", "RON")])
        cls.country_state = cls.env["res.country.state"].search([("name", "=", "București")])

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Strada Kunst, 3",
            'zip': "010101",
            'city': "Bucharest",
            'vat': 'RO1234567897',
            'phone': '+40 123 456 789',
            'email': 'info@partner1.ro',
            'country_id': cls.env.ref('base.ro').id,
            'currency_id': cls.currency.id,
            'state_id': cls.country_state.id,
            'bank_ids': [(0, 0, {'acc_number': 'RO11BTRL1234567890123456'})],
            'peppol_eas': '0106',
            'peppol_endpoint': '987654321',
            'ref': 'ref_partner_1',
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Bulevardul Europa, 2",
            'zip': "020202",
            'city': "Cluj-Napoca",
            'vat': 'RO1234567897',
            'country_id': cls.env.ref('base.ro').id,
            'currency_id': cls.currency.id,
            'state_id': cls.country_state.id,
            'bank_ids': [(0, 0, {'acc_number': 'RO22BTRL9876543210987654'})],
            'peppol_eas': '0106',
            'peppol_endpoint': '123456789',
            'ref': 'ref_partner_2',
        })

        cls.tax_19 = cls.env['account.tax'].create({
            'name': 'tax_19',
            'amount_type': 'percent',
            'amount': 19,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.ro').id,
        })

        cls.env.company.invoice_is_ubl_cii = True

    @classmethod
    def setup_company_data(cls, company_name, chart_template):
        # OVERRIDE
        # to force the company to be romanian
        res = super().setup_company_data(
            company_name,
            chart_template=chart_template,
            country_id=cls.env.ref("base.ro").id,
        )
        return res

    def test_anaf(self, invoice=None, manual_check=False):
        if not invoice:
            return
        invoice._generate_pdf_and_send_invoice(self.move_template)
        attachment = invoice.ubl_cii_xml_id
        self.assertTrue(attachment)
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
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 2.0,
                    'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
                    'price_unit': 123.0,
                    'discount': 10.0,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                    'currency_id': self.currency.id,
                },
            ],
        )
        self.test_anaf(invoice, True)
        # self.assertEqual(attachment.name[-11:], "cius_ro.xml")
