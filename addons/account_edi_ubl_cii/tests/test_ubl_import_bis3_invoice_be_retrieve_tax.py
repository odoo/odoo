from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBERetrieveTax(TestUblImportBis3InvoiceBE):

    _test_groups = None  # FIXME list needed groups

    def test_partial_import_tax_manual_tax_amounts(self):
        # Fail to retrieve the tax.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_manual_tax_amounts',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': [],
                },
                {
                    'quantity': 5.0,
                    'price_unit': 100.0,
                    'tax_ids': [],
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 1000.0,
                    'amount_tax': 0.0,
                    'amount_total': 1000.0,
                },
            ],
        )

        # Lines are linked to a single tax, the tax amount has been fixed
        tax_21 = self.percent_tax(21.0)
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_manual_tax_amounts',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 5.0,
                    'price_unit': 100.0,
                    'tax_ids': tax_21.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 1000.0,
                    'amount_tax': 210.01,
                    'amount_total': 1210.01,
                },
            ],
        )

    def test_partial_import_tax_charge_to_fixed_tax(self):
        tax_21 = self.percent_tax(21.0)

        # Fail to retrieve the tax.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_charge_to_fixed_tax',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 5.0,
                    'price_unit': 200.0,
                    'discount': 0.0,
                    'tax_ids': tax_21.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 1000.0,
                    'amount_tax': 210.0,
                    'amount_total': 1210.0,
                },
            ],
        )

        # Lines are linked to a single tax, the tax amount has been fixed
        recupel = self.fixed_tax(1.0, name='RECUPEL', include_base_amount=True, sequence=0)
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_charge_to_fixed_tax',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 5.0,
                    'price_unit': 199.0,
                    'discount': 0.0,
                    'tax_ids': (recupel + tax_21).ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 995.0,
                    'amount_tax': 215.0,
                    'amount_total': 1210.0,
                },
            ],
        )

    @freeze_time('2020-01-01')
    def test_partial_import_tax_manual_tax_amounts_invoice_predictive(self):
        self.ensure_installed('account_accountant')

        tax_21_1 = self.percent_tax(21.0)
        tax_21_2 = self.percent_tax(21.0)

        # First invoice to train the prediction.
        self._create_invoice(
            partner_id=self.partner_be,
            invoice_line_ids=[
                self._prepare_invoice_line(name="turlututu", price_unit=500.0, tax_ids=tax_21_1),
                self._prepare_invoice_line(name="tsointsoin", price_unit=500.0, tax_ids=tax_21_2),
            ],
            post=True,
        )

        # Check the prediction.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_manual_tax_amounts',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': tax_21_1.ids,
                },
                {
                    'quantity': 5.0,
                    'price_unit': 100.0,
                    'tax_ids': tax_21_2.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'partner_id': self.partner_be.id,
                    'amount_untaxed': 1000.0,
                    'amount_tax': 210.01,
                    'amount_total': 1210.01,
                },
            ],
        )

    def test_import_foreign_tax(self):
        domestic = self.env['account.chart.template'].ref('template_generic_domestic_fiscal_position')
        foreign_trade = self.env['account.chart.template'].ref('template_generic_export_fiscal_position')
        tax_21 = self.percent_tax(21.0, type_tax_use='sale')
        tax_21_foreign = self.percent_tax(21.0, type_tax_use='sale', fiscal_position_ids=foreign_trade)

        bill = self._import_invoice_as_attachment_on(test_name='test_partial_import_tax_manual_tax_amounts', journal=self.company_data["default_journal_sale"])
        partner = bill.partner_id
        self.assertEqual(bill.line_ids.tax_ids, tax_21_foreign)

        partner.property_account_position_id = domestic
        bill = self._import_invoice_as_attachment_on(test_name='test_partial_import_tax_manual_tax_amounts', journal=self.company_data["default_journal_sale"])
        partner = bill.partner_id
        self.assertEqual(bill.line_ids.tax_ids, tax_21)

    def test_partial_import_tax_included_invoice(self):
        tax_21 = self.percent_tax(21.0, price_include_override='tax_included')

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_manual_tax_amounts',
            journal=self.company_data['default_journal_sale'],
        )

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 605.0,
                    'discount': 0.0,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 5.0,
                    'price_unit': 121.0,
                    'discount': 0.0,
                    'tax_ids': tax_21.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 1000.0,
                    'amount_tax': 210.01,
                    'amount_total': 1210.01,
                },
            ],
        )
