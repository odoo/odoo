# Part of Odoo. See LICENSE file for full copyright and licensing details.

from textwrap import dedent


from odoo import Command
from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.addons.l10n_be_intrastat.tests.test_be_intrastat_report import TestBEIntrastatReport

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestBEIntrastatServicesReport(TestBEIntrastatReport):

    @classmethod
    @TestAccountReportsCommon.setup_country('be')
    def setUpClass(cls):
        super().setUpClass()
        italy = cls.env.ref('base.it')
        cls.report_services_handler = cls.env['account.intrastat.services.be.report.handler']
        cls.product_service_a = cls.env['product.product'].create({
            'name': 'Service A',
            'intrastat_code_id': cls.env.ref('l10n_be_intrastat_services.service_code_2022_B2001').id,
            'type': 'service',
        })
        cls.product_service_b = cls.env['product.product'].create({
            'name': 'Service B',
            'intrastat_code_id': cls.env.ref('l10n_be_intrastat_services.service_code_2022_B2101').id,
            'type': 'service',
        })
        cls.outwards_service_customer_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2022-05-15',
            'date': '2022-05-15',
            'intrastat_country_id': italy.id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [
                Command.create({
                    'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                    'intrastat_transaction_id': cls.env.ref(
                        'account_intrastat.account_intrastat_transaction_11'
                    ).id,
                    'product_id': cls.product_service_a.id,
                    'quantity': 4,
                    'price_unit': 250,
                }),
                Command.create({
                    'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                    'intrastat_transaction_id': cls.env.ref(
                        'account_intrastat.account_intrastat_transaction_11'
                    ).id,
                    'product_id': cls.product_service_b.id,
                    'quantity': 5,
                    'price_unit': 100,
                }),
            ],
        })
        cls.in_refund_service = cls.env["account.move"].create({
            "move_type": "in_refund",
            "partner_id": cls.partner_a.id,
            "invoice_date": "2022-05-15",
            "date": "2022-05-15",
            "intrastat_country_id": italy.id,
            "company_id": cls.company_data["company"].id,
            "invoice_line_ids": [Command.create({
                "product_uom_id": cls.env.ref("uom.product_uom_unit").id,
                "intrastat_transaction_id": cls.env.ref(
                    "account_intrastat.account_intrastat_transaction_11"
                ).id,
                "product_id": cls.product_service_a.id,
                "quantity": 4,
                "price_unit": 100,
            })],
        })
        cls.out_refund_service = cls.env["account.move"].create({
            "move_type": "out_refund",
            "partner_id": cls.partner_a.id,
            "invoice_date": "2022-05-15",
            "date": "2022-05-15",
            "intrastat_country_id": italy.id,
            "company_id": cls.company_data["company"].id,
            "invoice_line_ids": [Command.create({
                "product_uom_id": cls.env.ref("uom.product_uom_unit").id,
                "intrastat_transaction_id": cls.env.ref(
                    "account_intrastat.account_intrastat_transaction_11"
                ).id,
                "product_id": cls.product_service_a.id,
                "quantity": 4,
                "price_unit": 100,
            })],
        })

    def test_csv_goods_export(self):
        self.inwards_vendor_bill.action_post()
        self.outwards_customer_invoice.action_post()
        options = self._generate_options(self.report, '2022-05-01', '2022-05-31')
        options['intrastat_type'][0]['selected'] = True
        options['intrastat_type'][1]['selected'] = False
        csv = self.report_handler.be_intrastat_export_to_csv(options)['file_content']
        expected = '19;IT;11;;25309050;798.0;;23328;;\n'
        self.assertEqual(csv, expected)

    def test_csv_service_f02cms_export(self):
        self.outwards_service_customer_invoice.action_post()
        self.out_refund_service.action_post()
        self.in_refund_service.action_post()
        options = self._generate_options(self.report, '2022-05-01', '2022-05-31')
        csv = self.report_services_handler.be_intrastat_export_to_csv(options)['file_content']
        expected = dedent('''\
            B2001;IT;EUR;1400;400
            B2101;IT;EUR;500;0
            ''')
        self.assertEqual(csv, expected)

    def test_csv_service_non_intra_country_f02cms_export(self):
        self.partner_a.country_id = self.env.ref('base.us').id
        invoices = (
            self.outwards_service_customer_invoice +
            self.out_refund_service +
            self.in_refund_service
        )
        invoices.intrastat_country_id = None
        invoices.action_post()
        options = self._generate_options(self.report, '2022-05-01', '2022-05-31')
        csv = self.report_services_handler.be_intrastat_export_to_csv(options)['file_content']
        expected = dedent('''\
            B2001;US;EUR;1400;400
            B2101;US;EUR;500;0
            ''')
        self.assertEqual(csv, expected)

    def test_csv_service_f01dgs_export(self):
        self.outwards_service_customer_invoice.action_post()
        self.out_refund_service.action_post()
        self.in_refund_service.action_post()
        report = self.env.ref('l10n_be_intrastat_services.intrastat_report_services_f01dgs')
        options = self._generate_options(report, '2022-05-01', '2022-05-31')
        csv = self.report_services_handler.be_intrastat_export_to_csv(options)['file_content']
        expected = dedent('''\
            B2001;IT;EUR;1400;400
            B2001CN;IT;EUR;400;400
            B2101;IT;EUR;500;0
            ''')
        self.assertEqual(csv, expected)
