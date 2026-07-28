# -*- coding: utf-8 -*-
from freezegun import freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.fields import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestInvoiceHSNsummary(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(chart_template_ref='in')

        cls.test_hsn_code_1 = '1234'
        cls.test_hsn_code_2 = '4321'

        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')

        cls.product_a.l10n_in_hsn_code = cls.test_hsn_code_1
        cls.product_b.l10n_in_hsn_code = cls.test_hsn_code_2
        cls.product_c = cls.env['product.product'].create({
            'name': 'product_c',
            'l10n_in_hsn_code': cls.test_hsn_code_1,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
        })

        cls.gst_5 = cls.env['account.chart.template'].ref('sgst_sale_5')
        cls.gst_18 = cls.env['account.chart.template'].ref('sgst_sale_18')

        cls.igst_0 = cls.env['account.chart.template'].ref('igst_sale_0')
        cls.igst_5 = cls.env['account.chart.template'].ref('igst_sale_5')
        cls.igst_18 = cls.env['account.chart.template'].ref('igst_sale_18')
        cls.cess_5_plus_1591 = cls.env['account.chart.template'].ref('cess_5_plus_1591_sale')
        cls.exempt_0 = cls.env['account.chart.template'].ref('exempt_sale')

        cls.display_uom = cls.env.user.user_has_groups('uom.group_uom')

    def assert_hsn_summary(self, invoice, expected_values):
        hsn_summary = invoice._l10n_in_get_hsn_summary_table()
        self.assertEqual(
            {k: len(v) if k == 'items' else v for k, v in hsn_summary.items()},
            {k: len(v) if k == 'items' else v for k, v in expected_values.items()},
        )
        self.assertEqual(len(hsn_summary['items']), len(expected_values['items']))
        for item, expected_item in zip(hsn_summary['items'], expected_values['items']):
            self.assertDictEqual(item, expected_item)

    @freeze_time('2019-01-01')
    def create_invoice(self, invoice_line_ids, **kwargs):
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            **kwargs,
            'invoice_line_ids': invoice_line_ids,
        })

    def test_l10n_in_hsn_summary_1(self):
        """ Test GST/IGST taxes. """
        invoice = self.create_invoice(invoice_line_ids=[
            Command.create({
                'product_id': self.product_a.id,
                'quantity': 2.0,
                'price_unit': 100,
                'tax_ids': [Command.set(self.gst_5.ids)], #Tax: 10
            }),
            Command.create({
                'product_id': self.product_c.id,
                'quantity': 1.0,
                'price_unit': 600,
                'tax_ids': [Command.set(self.gst_5.ids)], #Tax: 30
            }),
            Command.create({
                'product_id': self.product_a.id,
                'quantity': 2.0,
                'price_unit': 100,
                'tax_ids': [Command.set(self.gst_18.ids)], #Tax: 36
            }),
            Command.create({
                'product_id': self.product_c.id,
                'quantity': 1.0,
                'price_unit': 600,
                'tax_ids': [Command.set(self.gst_18.ids)], #Tax: 108
            }),
        ])

        self.assertRecordValues(invoice, [{
            'amount_untaxed': 1600.0,
            'amount_tax': 184.0,
            'amount_total': 1784.0,
        }])

        self.assert_hsn_summary(invoice, {
            'has_igst': False,
            'has_gst': True,
            'has_cess': False,
            'nb_columns': 7,
            'display_uom': self.display_uom,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 3.0,
                    'uom': self.uom_unit,
                    'rate': 5.0,
                    'amount_untaxed': 800.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 20.0,
                    'tax_amount_sgst': 20.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 3.0,
                    'uom': self.uom_unit,
                    'rate': 18.0,
                    'amount_untaxed': 800.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 72.0,
                    'tax_amount_sgst': 72.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        })

        # Change the UOM of the second line.
        invoice.invoice_line_ids = [
            Command.update(invoice.invoice_line_ids[1].id, {'product_uom_id': self.uom_dozen.id}),
        ]

        self.assertRecordValues(invoice, [{
            'amount_untaxed': 13000.0,
            'amount_tax': 754.0,
            'amount_total': 13754.0,
        }])

        self.assert_hsn_summary(invoice, {
            'has_igst': False,
            'has_gst': True,
            'has_cess': False,
            'nb_columns': 7,
            'display_uom': self.display_uom,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 2.0,
                    'uom': self.uom_unit,
                    'rate': 5.0,
                    'amount_untaxed': 200.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 5.0,
                    'tax_amount_sgst': 5.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom': self.uom_dozen,
                    'rate': 5.0,
                    'amount_untaxed': 12000.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 300.0,
                    'tax_amount_sgst': 300.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 3.0,
                    'uom': self.uom_unit,
                    'rate': 18.0,
                    'amount_untaxed': 800.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 72.0,
                    'tax_amount_sgst': 72.0,
                    'tax_amount_cess': 0.0,
                }
            ]
        })

        # Change GST 5% taxes to IGST.
        invoice.invoice_line_ids = [
            Command.update(invoice.invoice_line_ids[0].id, {'tax_ids': [Command.set(self.igst_5.ids)]}),
            Command.update(invoice.invoice_line_ids[1].id, {'tax_ids': [Command.set(self.igst_5.ids)]}),
            Command.update(invoice.invoice_line_ids[2].id, {'tax_ids': [Command.set(self.igst_5.ids)]}),
        ]

        self.assertRecordValues(invoice, [{
            'amount_untaxed': 13000.0,
            'amount_tax': 728.0,
            'amount_total': 13728.0,
        }])

        self.assert_hsn_summary(invoice, {
            'has_igst': True,
            'has_gst': True,
            'has_cess': False,
            'nb_columns': 8,
            'display_uom': self.display_uom,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 4.0,
                    'uom': self.uom_unit,
                    'rate': 5.0,
                    'amount_untaxed': 400.0,
                    'tax_amount_igst': 20.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom': self.uom_dozen,
                    'rate': 5.0,
                    'amount_untaxed': 12000.0,
                    'tax_amount_igst': 600.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom': self.uom_unit,
                    'rate': 18.0,
                    'amount_untaxed': 600.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 54.0,
                    'tax_amount_sgst': 54.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        })

        # Put back the UOM of the second line to unit.
        invoice.invoice_line_ids = [
            Command.update(invoice.invoice_line_ids[1].id, {
                'product_uom_id': self.uom_unit.id,
                'price_unit': 600,
                'tax_ids': [Command.set(self.igst_5.ids)],
            }),
        ]

        self.assertRecordValues(invoice, [{
            'amount_untaxed': 1600.0,
            'amount_tax': 158.0,
            'amount_total': 1758.0,
        }])

        self.assert_hsn_summary(invoice, {
            'has_igst': True,
            'has_gst': True,
            'has_cess': False,
            'nb_columns': 8,
            'display_uom': self.display_uom,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 5.0,
                    'uom': self.uom_unit,
                    'rate': 5.0,
                    'amount_untaxed': 1000.0,
                    'tax_amount_igst': 50.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom': self.uom_unit,
                    'rate': 18.0,
                    'amount_untaxed': 600.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 54.0,
                    'tax_amount_sgst': 54.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        })

        # Change GST 18% taxes to IGST.
        invoice.invoice_line_ids = [
            Command.update(invoice.invoice_line_ids[3].id, {'tax_ids': [Command.set(self.igst_18.ids)]}),
        ]

        self.assert_hsn_summary(invoice, {
            'has_igst': True,
            'has_gst': False,
            'has_cess': False,
            'nb_columns': 6,
            'display_uom': self.display_uom,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 5.0,
                    'uom': self.uom_unit,
                    'rate': 5.0,
                    'amount_untaxed': 1000.0,
                    'tax_amount_igst': 50.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom': self.uom_unit,
                    'rate': 18.0,
                    'amount_untaxed': 600.0,
                    'tax_amount_igst': 108.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        })

    def test_l10n_in_hsn_summary_2(self):
        """ Test CESS taxes in combination with GST/IGST. """
        invoice = self.create_invoice(invoice_line_ids=[
            Command.create({
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'price_unit': 15.80,
                'product_uom_id': self.uom_unit.id,
                'tax_ids': [Command.set((self.gst_18 + self.cess_5_plus_1591).ids)],
            })
        ])

        self.assertRecordValues(invoice, [{
            'amount_untaxed': 15.8,
            'amount_tax': 5.22,
            'amount_total': 21.02,
        }])

        self.assert_hsn_summary(invoice, {
            'has_igst': False,
            'has_gst': True,
            'has_cess': True,
            'nb_columns': 8,
            'display_uom': self.display_uom,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom': self.uom_unit,
                    'rate': 18.0,
                    'amount_untaxed': 15.8,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 1.42,
                    'tax_amount_sgst': 1.42,
                    'tax_amount_cess': 2.38,
                },
            ],
        })

        # Change GST 18% taxes to IGST.
        invoice.invoice_line_ids = [
            Command.update(invoice.invoice_line_ids.id, {
                'tax_ids': [Command.set((self.igst_18 + self.cess_5_plus_1591).ids)],
            }),
        ]

        self.assert_hsn_summary(invoice, {
            'has_igst': True,
            'has_gst': False,
            'has_cess': True,
            'nb_columns': 7,
            'display_uom': self.display_uom,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom': self.uom_unit,
                    'rate': 18.0,
                    'amount_untaxed': 15.8,
                    'tax_amount_igst': 2.84,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 2.38,
                },
            ],
        })

    def test_l10n_in_hsn_summary_3(self):
        """ Test with mixed HSN codes. """
        invoice = self.create_invoice(invoice_line_ids=[
            Command.create({
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'price_unit': 100,
                'product_uom_id': self.uom_unit.id,
                'tax_ids': [Command.set(self.gst_18.ids)],
            }),
            Command.create({
                'product_id': self.product_b.id,
                'quantity': 1.0,
                'price_unit': 100,
                'product_uom_id': self.uom_unit.id,
                'tax_ids': [Command.set(self.gst_18.ids)],
            }),
        ])

        self.assertRecordValues(invoice, [{
            'amount_untaxed': 200.0,
            'amount_tax': 36.0,
            'amount_total': 236.0,
        }])

        self.assert_hsn_summary(invoice, {
            'has_igst': False,
            'has_gst': True,
            'has_cess': False,
            'nb_columns': 7,
            'display_uom': self.display_uom,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom': self.uom_unit,
                    'rate': 18.0,
                    'amount_untaxed': 100.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 9.0,
                    'tax_amount_sgst': 9.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_2,
                    'quantity': 1.0,
                    'uom': self.uom_unit,
                    'rate': 18.0,
                    'amount_untaxed': 100.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 9.0,
                    'tax_amount_sgst': 9.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        })

        # Change GST 18% taxes to IGST.
        invoice.invoice_line_ids = [
            Command.update(invoice.invoice_line_ids[0].id, {'tax_ids': [Command.set(self.igst_18.ids)]}),
            Command.update(invoice.invoice_line_ids[1].id, {'tax_ids': [Command.set(self.igst_18.ids)]}),
        ]

        self.assert_hsn_summary(invoice, {
            'has_igst': True,
            'has_gst': False,
            'has_cess': False,
            'nb_columns': 6,
            'display_uom': self.display_uom,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom': self.uom_unit,
                    'rate': 18.0,
                    'amount_untaxed': 100.0,
                    'tax_amount_igst': 18.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_2,
                    'quantity': 1.0,
                    'uom': self.uom_unit,
                    'rate': 18.0,
                    'amount_untaxed': 100.0,
                    'tax_amount_igst': 18.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        })

    def test_l10n_in_hsn_summary_4(self):
        """ Zero rated GST or no taxes at all."""
        invoice = self.create_invoice(invoice_line_ids=[
            Command.create({
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'price_unit': 350.0,
                'product_uom_id': self.uom_unit.id,
                'tax_ids': [],
            }),
            Command.create({
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'price_unit': 350.0,
                'product_uom_id': self.uom_unit.id,
                'tax_ids': [],
            }),
        ])

        self.assert_hsn_summary(invoice, {
            'has_igst': False,
            'has_gst': False,
            'has_cess': False,
            'nb_columns': 5,
            'display_uom': self.display_uom,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 2.0,
                    'uom': self.uom_unit,
                    'rate': 0.0,
                    'amount_untaxed': 700.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        })

        # No tax to IGST 0%/exempt.
        invoice.invoice_line_ids = [
            Command.update(invoice.invoice_line_ids[0].id, {'tax_ids': [Command.set(self.igst_0.ids)]}),
            Command.update(invoice.invoice_line_ids[1].id, {'tax_ids': [Command.set(self.exempt_0.ids)]}),
        ]

        self.assert_hsn_summary(invoice, {
            'has_igst': False,
            'has_gst': False,
            'has_cess': False,
            'nb_columns': 5,
            'display_uom': self.display_uom,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 2.0,
                    'uom': self.uom_unit,
                    'rate': 0.0,
                    'amount_untaxed': 700.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        })

        # Put one IGST 18% to get a value on the IGST column.
        invoice.invoice_line_ids = [
            Command.update(invoice.invoice_line_ids[0].id, {'tax_ids': [Command.set(self.igst_18.ids)]}),
        ]

        self.assert_hsn_summary(invoice, {
            'has_igst': True,
            'has_gst': False,
            'has_cess': False,
            'nb_columns': 6,
            'display_uom': self.display_uom,
            'items': [
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom': self.uom_unit,
                    'rate': 18.0,
                    'amount_untaxed': 350.0,
                    'tax_amount_igst': 63.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
                {
                    'l10n_in_hsn_code': self.test_hsn_code_1,
                    'quantity': 1.0,
                    'uom': self.uom_unit,
                    'rate': 0.0,
                    'amount_untaxed': 350.0,
                    'tax_amount_igst': 0.0,
                    'tax_amount_cgst': 0.0,
                    'tax_amount_sgst': 0.0,
                    'tax_amount_cess': 0.0,
                },
            ],
        })
