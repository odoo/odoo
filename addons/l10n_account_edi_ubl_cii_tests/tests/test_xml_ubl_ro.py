# -*- coding: utf-8 -*-

import base64

from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.tests import tagged
from odoo.tools.misc import file_open
from lxml import etree
from odoo import Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLRO(TestUBLCommon, TestAccountMoveSendCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="ro"):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Strada Kunst, 3",
            'zip': "010101",
            'city': "Bucharest",
            'vat': 'RO1234567897',
            'phone': '+40 123 456 789',
            'email': 'info@partner1.com',
            'country_id': cls.env.ref('base.ro').id,
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
            'bank_ids': [(0, 0, {'acc_number': 'RO22BTRL9876543210987654'})],
            'peppol_eas': '0106',
            'peppol_endpoint': '123456789',
            'ref': 'ref_partner_2',
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
            vat="RO1234567897")
        return res

    ####################################################
    # Test export - import
    ####################################################

    def test_export_invoice_one_line_schematron_partner_ro(self):
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
                    # 'tax_ids': [(6, 0, self.tax_19.ids)],
                },
            ],
        )
        # invoice = self.env["account.move"].create({
        #     'move_type': 'out_invoice',
        #     'partner_id': self.partner_1.id,
        #     'partner_bank_id': self.env.company.partner_id.bank_ids[:1].id,
        #     'invoice_payment_term_id': self.pay_terms_b.id,
        #     # 'invoice_date': '2017-01-01',
        #     # 'date': '2017-01-01',
        #     # 'narration': 'test narration',
        #     'ref': 'ref_move',
        #     'invoice_line_ids': [
        #         Command.create({
        #             'product_id': self.product_a.id,
        #             'quantity': 1.0,
        #             'price_unit': 1000.0,
        #             'tax_ids': [Command.set(self.env["account.chart.template"].ref('tax110').ids)],
        #         }),
        #     ],
        # })
        # invoice.action_post()

        invoice._generate_pdf_and_send_invoice(self.move_template)
        self.assertTrue(invoice.ubl_cii_xml_id)
        # self.assertFalse(invoice.ubl_cii_xml_id)
        # self.assertFalse(invoice.ubl_cii_xml_id)
        # self.assertTrue(invoice.ubl_cii_xml_id)
        # self.assertFalse(invoice.ubl_cii_xml_id)
        # self.assertFalse(invoice.ubl_cii_xml_id)

        # xml_content = base64.b64decode(invoice.ubl_cii_xml_id.with_context(bin_size=False).datas)
        # xml_etree = self.get_xml_tree_from_string(xml_content)

        # from pathlib import Path
        # with Path("~/Downloads/OIOUBL.xml").expanduser().open("wb") as f:
        #     f.write(xml_content)
        # with file_open("l10n_account_edi_ubl_cii_tests/tests/OIOUBL_Invoice_Schematron.xsl", "rb") as schematron_file:
        #     xsl = etree.parse(schematron_file)
        #     transform = etree.XSLT(xsl)
        #     result_tree = transform(xml_etree)

        #     errors = result_tree.xpath("//Error")
        #     err = False
        #     for error in errors:
        #         err = True
        #         print("")
        #         print("")
        #         print(error.xpath("//Xpath")[0].text)
        #         print(error.xpath("//Description")[0].text)
        #         print("")
        #         print(error.xpath("//Pattern")[0].text)
        #     self.assertFalse(err, "There is some error detected by the schematron")
