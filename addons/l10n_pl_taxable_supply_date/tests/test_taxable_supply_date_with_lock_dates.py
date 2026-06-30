from odoo import Command, fields
from odoo.tests import Form, freeze_time, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
@freeze_time('2025-06-23')
class TestTaxableSupplyDateWithLockDates(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('pl')
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR', rates=[
            ('2026-06-01',1),
            ('2026-06-02',2),
            ('2026-06-03',3)])
        company_id = cls.company_data['company']
        company_id.purchase_lock_date = fields.Date.from_string('2025-04-30')
        company_id.tax_lock_date = fields.Date.from_string('2025-03-31')

    def check_invoice_dates(self, move_type, post, invoice_date, taxable_supply_date, expected_accounting_date, is_banner_expected):
        # data creation
        tax = self.tax_sale_a if move_type in self.env['account.move'].get_sale_types() else self.tax_purchase_a

        move_form = Form(self.env['account.move'].with_context(default_move_type=move_type))
        move_form.invoice_date = invoice_date
        move_form.partner_id = self.partner_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.name = "test line"
            line_form.price_unit = 1
            line_form.tax_ids.add(tax)
        if taxable_supply_date:
            move_form.taxable_supply_date = fields.Date.from_string(taxable_supply_date)

        move = move_form.save()
        if post:
            move.action_post()

        # assertion
        self.assertEqual(move.date, fields.Date.from_string(expected_accounting_date), "Accounting date should have been %s" % expected_accounting_date)
        if is_banner_expected:
            self.assertNotEqual(move.tax_lock_date_message, False)
        else:
            self.assertEqual(move.tax_lock_date_message, False)

    def test_invoice_taxable_supply_date_with_lock_dates(self):
        for move_type in ['out_invoice', 'out_refund']:
            self.check_invoice_dates(
                move_type=move_type,
                post=False,
                invoice_date='2025-05-05',
                taxable_supply_date=None,
                expected_accounting_date='2025-05-05',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=True,
                invoice_date='2025-05-05',
                taxable_supply_date=None,
                expected_accounting_date='2025-05-05',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=False,
                invoice_date='2025-03-03',
                taxable_supply_date=None,
                expected_accounting_date='2025-03-03',
                is_banner_expected=True,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=True,
                invoice_date='2025-03-03',
                taxable_supply_date=None,
                expected_accounting_date='2025-06-23',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=False,
                invoice_date='2025-05-05',
                taxable_supply_date='2025-03-20',
                expected_accounting_date='2025-03-20',
                is_banner_expected=True,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=True,
                invoice_date='2025-05-05',
                taxable_supply_date='2025-03-20',
                expected_accounting_date='2025-06-23',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=False,
                invoice_date='2025-03-03',
                taxable_supply_date='2025-03-20',
                expected_accounting_date='2025-03-20',
                is_banner_expected=True,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=True,
                invoice_date='2025-03-03',
                taxable_supply_date='2025-03-20',
                expected_accounting_date='2025-06-23',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=False,
                invoice_date='2025-05-05',
                taxable_supply_date='2025-05-15',
                expected_accounting_date='2025-05-15',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=True,
                invoice_date='2025-05-05',
                taxable_supply_date='2025-05-15',
                expected_accounting_date='2025-05-15',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=False,
                invoice_date='2025-03-03',
                taxable_supply_date='2025-05-15',
                expected_accounting_date='2025-05-15',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=True,
                invoice_date='2025-03-03',
                taxable_supply_date='2025-05-15',
                expected_accounting_date='2025-05-15',
                is_banner_expected=False,
            )

    def test_bill_taxable_supply_date_with_lock_dates(self):
        for move_type in ['in_invoice', 'in_refund']:
            self.check_invoice_dates(
                move_type=move_type,
                post=False,
                invoice_date='2025-05-05',
                taxable_supply_date=None,
                expected_accounting_date='2025-05-31',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=True,
                invoice_date='2025-05-05',
                taxable_supply_date=None,
                expected_accounting_date='2025-05-31',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=False,
                invoice_date='2025-03-03',
                taxable_supply_date=None,
                expected_accounting_date='2025-05-31',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=True,
                invoice_date='2025-03-03',
                taxable_supply_date=None,
                expected_accounting_date='2025-05-31',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=False,
                invoice_date='2025-05-05',
                taxable_supply_date='2025-03-20',
                expected_accounting_date='2025-05-31',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=True,
                invoice_date='2025-05-05',
                taxable_supply_date='2025-03-20',
                expected_accounting_date='2025-05-31',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=False,
                invoice_date='2025-03-03',
                taxable_supply_date='2025-03-20',
                expected_accounting_date='2025-05-31',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=True,
                invoice_date='2025-03-03',
                taxable_supply_date='2025-03-20',
                expected_accounting_date='2025-05-31',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=False,
                invoice_date='2025-05-05',
                taxable_supply_date='2025-05-15',
                expected_accounting_date='2025-05-31',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=True,
                invoice_date='2025-05-05',
                taxable_supply_date='2025-05-15',
                expected_accounting_date='2025-05-31',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=False,
                invoice_date='2025-03-03',
                taxable_supply_date='2025-05-15',
                expected_accounting_date='2025-05-31',
                is_banner_expected=False,
            )

            self.check_invoice_dates(
                move_type=move_type,
                post=True,
                invoice_date='2025-03-03',
                taxable_supply_date='2025-05-15',
                expected_accounting_date='2025-05-31',
                is_banner_expected=False,
            )

    @freeze_time('2026-06-02')
    def test_currency_rate_manual_change(self):
        """
        Ensure that if invoice_currency_rate is manually set and invoice_date is not set,
        posting the invoice doesn't change the currency rate back to default
        """
        invoice1 = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'invoice_date': False,
            'taxable_supply_date': '2026-06-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 60})],
            'currency_id': self.other_currency.id,
        }])
        self.assertEqual(invoice1.invoice_currency_rate, 1.0)
        self.env.cr.execute(f""" UPDATE account_move SET create_date = '2026-06-02' where id  = {invoice1.id}""")
        invoice1.invalidate_recordset(['create_date'])
        # currency rate of the invoice creation date that will be computed on action_post
        invoice1.invoice_currency_rate = 2
        invoice1.action_post()
        self.assertRecordValues(invoice1.line_ids, [
            {'amount_currency':   -60.0, 'balance':   -30.0},  # Product line
            {'amount_currency':    60.0, 'balance':    30.0},  # Receivable line
        ])
        invoice1.button_draft()
        invoice1.invoice_date = False
        invoice1.invoice_currency_rate = 2
        with freeze_time('2026-06-03'):
            invoice1.action_post()
        self.assertRecordValues(invoice1.line_ids, [
            {'amount_currency':   -60.0, 'balance':   -30.0},  # Product line
            {'amount_currency':    60.0, 'balance':    30.0},  # Receivable line
        ])
