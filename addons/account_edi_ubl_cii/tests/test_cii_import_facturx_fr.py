from odoo import fields
from odoo.addons.account_edi_ubl_cii.tests.common import TestCiiFacturXCommon, TestUblCiiFRCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class CiiImportFacturXFR(TestCiiFacturXCommon, TestUblCiiFRCommon):

    @classmethod
    def subfolders(cls):
        subfolder_format, _subfolder_document, subfolder_country = super().subfolders()
        return subfolder_format, 'invoice', subfolder_country

    @classmethod
    def _create_partner_fr(cls, **kwargs):
        partner = super()._create_partner_fr(**kwargs)
        partner.write({'invoice_edi_format': 'facturx'})
        return partner

    def test_import_invoice_deferred_and_delivery_dates(self):
        tax_20 = self.percent_tax(20.0)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_invoice_deferred_and_delivery_dates',
            journal=self.company_data['default_journal_sale'],
        )

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                    'tax_ids': tax_20.ids,
                    'deferred_start_date': fields.Date.from_string("2026-02-01"),
                    'deferred_end_date': fields.Date.from_string("2026-05-01"),
                },
                {
                    'quantity': 3.0,
                    'price_unit': 2000.0,
                    'tax_ids': tax_20.ids,
                    'deferred_start_date': fields.Date.from_string("2026-03-01"),
                    'deferred_end_date': fields.Date.from_string("2026-06-01"),
                },
            ],
        )

        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 7000.0,
                    'amount_tax': 1400.0,
                    'amount_total': 8400.0,
                    'invoice_date': fields.Date.from_string("2026-01-01"),
                    'invoice_date_due': fields.Date.from_string("2026-01-31"),
                    'delivery_date': fields.Date.from_string("2026-01-15"),
                },
            ],
        )

    def test_import_invoice_eco_tax_and_discount(self):
        tax_recupel = self.fixed_tax(1.0, name="RECUPEL", include_base_amount=True)
        tax_auvibel = self.fixed_tax(2.0, name="AUVIBEL", include_base_amount=True)
        tax_bebat = self.fixed_tax(3.0, name="BEBAT", include_base_amount=True)
        tax_20 = self.percent_tax(20.0)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_invoice_eco_tax_and_discount',
            journal=self.company_data['default_journal_sale'],
        )

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1,
                    'price_unit': 99.0,
                    'tax_ids': (tax_recupel + tax_20).ids,
                    'discount': 0.0,
                    'price_subtotal': 99.0,
                },
                {
                    'quantity': 4.0,
                    'price_unit': 98.0,
                    'tax_ids': (tax_auvibel + tax_20).ids,
                    'discount': 25.0,
                    'price_subtotal': 294.0,
                },
                {
                    'quantity': 1.0,
                    'price_unit': 97.0,
                    'tax_ids': (tax_bebat + tax_20).ids,
                    'discount': 0.0,
                    'price_subtotal': 97.0,
                },
            ],
        )

        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 490.0,
                    'amount_tax': 112.4,
                    'amount_total': 602.4,
                }
            ]
        )

    def test_import_invoice_product_uom_and_negative_qty(self):
        tax_20 = self.percent_tax(20.0)
        uom_unit = self.ref("uom.product_uom_unit")
        uom_dozen = self.ref("uom.product_uom_dozen")

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_invoice_product_uom_and_negative_qty',
            journal=self.company_data['default_journal_sale'],
        )

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 2,
                    'price_unit': 990.0,
                    'tax_ids': tax_20.ids,
                    'discount': 10.0,
                    'product_uom_id': uom_dozen,
                    'price_subtotal': 1782.0,
                },
                {
                    'quantity': 10.0,
                    'price_unit': 100.0,
                    'tax_ids': tax_20.ids,
                    'discount': 0.0,
                    'product_uom_id': uom_unit,
                    'price_subtotal': 1000.0,
                },
                {
                    'quantity': -1.0,
                    'price_unit': 100.0,
                    'tax_ids': tax_20.ids,
                    'discount': 0.0,
                    'product_uom_id': uom_unit,
                    'price_subtotal': -100.0,
                },
            ],
        )
