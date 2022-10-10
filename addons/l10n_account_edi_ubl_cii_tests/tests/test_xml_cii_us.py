# -*- coding: utf-8 -*-

from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.tests import tagged

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCIIUS(TestUBLCommon):

    @classmethod
    def setUpClass(cls,
                   chart_template_ref=None,
                   edi_format_ref="account_edi_ubl_cii.edi_facturx_1_0_05",
                   ):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'country_id': cls.env.ref('base.us').id,
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'country_id': cls.env.ref('base.us').id,
        })

    @classmethod
    def setup_company_data(cls, company_name, chart_template):
        # OVERRIDE
        res = super().setup_company_data(
            company_name,
            chart_template=chart_template,
            country_id=cls.env.ref("base.us").id,
        )
        return res

    def test_print_pdf_us_company(self):
        """ Even for a US company, a printed PDF should contain a Factur-X xml
        """
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 2.0,
                    'price_unit': 990.0,
                },
            ],
        )
        collected_streams = self.env['ir.actions.report']._render_qweb_pdf_prepare_streams(
            report_ref='account.report_invoice_with_payments',
            data=None,
            res_ids=invoice.ids,
        )
        self.assertTrue(
            bytes("<rsm:CrossIndustryInvoice", 'utf8') in collected_streams[invoice.id]['stream'].getvalue(),
            "Any invoice's PDF should contain a factur-x.xml"
        )

    def test_import_facturx_us_company(self):
        """ Even for a US company, importing a PDF containing a Factur-X xml
        should create the correct invoice
        """
        self._assert_imported_invoice_from_file(
            subfolder='tests/test_files/from_factur-x_doc',
            filename='facturx_invoice_negative_amounts.xml',
            amount_total=90,
            amount_tax=0,
            list_line_subtotals=[-5, 10, 60, 30, 5, 0, -10],
            move_type='in_refund'
        )
