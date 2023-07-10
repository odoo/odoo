# -*- coding: utf-8 -*-

import base64

from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.tests import tagged
from odoo.tools.misc import file_open
from lxml import etree, isoschematron
from odoo import Command

from saxonpy import PySaxonProcessor


# TODO - remove 'yoni' tag when done
@tagged('post_install_l10n', 'post_install', '-at_install', 'yoni')
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

        invoice._generate_pdf_and_send_invoice(self.move_template)
        attachment = invoice.ubl_cii_xml_id
        self.assertTrue(attachment)
        xml_content = base64.b64decode(attachment.with_context(bin_size=False).datas)

        # TODO: remove when done
        # for manual check to https://www.anaf.ro/uploadxmi/
        from pathlib import Path
        with Path("~/work/odoo/.notes/test.xml").expanduser().open("wb") as f:
            f.write(xml_content)

        self.assertEqual(attachment.name[-11:], "cius_ro.xml")

        # with PySaxonProcessor(license=False) as proc:
        #     xsltproc = proc.new_xslt_processor()
        #     document = proc.parse_xml(xml_text=xml_content)
        #     xsltproc.set_source(xdm_node=document)
        #     xsltproc.compile_stylesheet(stylesheet_text="<xsl:stylesheet xmlns:xsl='http://www.w3.org/1999/XSL/Transform' version='2.0'> <xsl:param name='values' select='(2,3,4)' /><xsl:output method='xml' indent='yes' /><xsl:template match='*'><output><xsl:value-of select='//person[1]'/><xsl:for-each select='$values' ><out><xsl:value-of select='. * 3'/></out></xsl:for-each></output></xsl:template></xsl:stylesheet>")
        #     xsltproc.compile_stylesheet(stylesheet_text="<xsl:stylesheet xmlns:xsl='http://www.w3.org/1999/XSL/Transform' version='2.0'> <xsl:param name='values' select='(2,3,4)' /><xsl:output method='xml' indent='yes' /><xsl:template match='*'><output><xsl:value-of select='//person[1]'/><xsl:for-each select='$values' ><out><xsl:value-of select='. * 3'/></out></xsl:for-each></output></xsl:template></xsl:stylesheet>")
        #     output2 = xsltproc.transform_to_string()
        #     print(output2)

        # schematron_path = 'l10n_account_edi_ubl_cii_tests/tests/test_files/from_odoo/ciusro_EN16931-UBL-validation.sch'
        # with file_open(schematron_path, "rb") as schematron_file:
        #     xslt_content = schematron_file.read()

        # xslt_etree = etree.fromstring(xslt_content)
        # transformer = etree.XSLT(xslt_etree)
        # result = transformer(xml_etree)
        # validation_result = str(result)

        #     sch_doc = etree.parse(schematron_file)
        #     schematron = isoschematron.Schematron(sch_doc, store_report=True)
        #     validation_result = schematron.validate(xml_etree)

        #     with Path("~/work/odoo/.notes/result.xml").expanduser().open("wb") as f:
        #         f.write(validation_result)

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
