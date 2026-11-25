from freezegun import freeze_time

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMoveSyncTaxLines(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tax_21 = cls.percent_tax(cls, 21.0)
        cls.tax_6 = cls.percent_tax(cls, 6.0)
        cls.eur = cls.setup_other_currency('EUR', rates=[
            ('2017-01-01', 2.0),
            ('2018-01-01', 4.0),
        ])

    def test_create_invoice_one_taxed_line(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -21.0, 'balance':  -21.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  121.0, 'balance':  121.0},
        ])

    def test_update_base_line_price(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids.id, {'price_unit': 200})]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -200.0, 'balance': -200.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -42.0, 'balance':  -42.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  242.0, 'balance':  242.0},
        ])

    def test_remove_tax_from_base_line(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids.id, {'tax_ids': [Command.clear()]})]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False, 'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'payment_term', 'tax_line_id': False, 'amount_currency':  100.0, 'balance':  100.0},
        ])

    def test_two_base_lines_same_tax(self):
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
            self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_21),
        ])

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -200.0, 'balance': -200.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -63.0, 'balance':  -63.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  363.0, 'balance':  363.0},
        ])

    def test_two_base_lines_different_taxes(self):
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
            self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_6),
        ])

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -200.0, 'balance': -200.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -21.0, 'balance':  -21.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_6.id,  'amount_currency':  -12.0, 'balance':  -12.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  333.0, 'balance':  333.0},
        ])

    def test_delete_base_line(self):
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
            self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_21),
        ])

        invoice.invoice_line_ids = [Command.delete(invoice.invoice_line_ids[1].id)]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -21.0, 'balance':  -21.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  121.0, 'balance':  121.0},
        ])

    def test_change_tax_on_base_line(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids.id, {'tax_ids': [Command.set(self.tax_6.ids)]})]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,         'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'payment_term', 'tax_line_id': False,         'amount_currency':  106.0, 'balance':  106.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_6.id, 'amount_currency':   -6.0, 'balance':   -6.0},
        ])

    def test_foreign_currency(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21, currency_id=self.eur, invoice_date='2017-01-01')

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -50.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -21.0, 'balance': -10.5},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  121.0, 'balance':  60.5},
        ])

    def test_manual_tax_amount(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -30.0, 'balance':  -30.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  130.0, 'balance':  130.0},
        ])

    def test_manual_tax_amount_kept_when_adding_untaxed_line(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]
        invoice.invoice_line_ids = [self._prepare_invoice_line(price_unit=50)]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -30.0, 'balance':  -30.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  180.0, 'balance':  180.0},
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency':  -50.0, 'balance':  -50.0},
        ])

    def test_manual_tax_amount_kept_when_updating_line_with_other_tax(self):
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
            self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_6),
        ])

        tax_line_21 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_21)
        invoice.line_ids = [Command.update(tax_line_21.id, {'amount_currency': -30.0})]
        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids[1].id, {'price_unit': 300})]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -300.0, 'balance': -300.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -30.0, 'balance':  -30.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_6.id,  'amount_currency':  -18.0, 'balance':  -18.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  448.0, 'balance':  448.0},
        ])

    def test_manual_tax_amount_recomputed_when_updating_its_base_line(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]
        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids.id, {'price_unit': 200})]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -200.0, 'balance': -200.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -42.0, 'balance':  -42.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  242.0, 'balance':  242.0},
        ])

    def test_manual_tax_amount_kept_when_adding_line_with_other_tax(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]
        invoice.invoice_line_ids = [self._prepare_invoice_line(price_unit=50, tax_ids=self.tax_6)]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -30.0, 'balance':  -30.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  183.0, 'balance':  183.0},
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency':  -50.0, 'balance':  -50.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_6.id,  'amount_currency':   -3.0, 'balance':   -3.0},
        ])

    def test_manual_tax_amount_recomputed_when_adding_line_with_same_tax(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]
        invoice.invoice_line_ids = [self._prepare_invoice_line(price_unit=50, tax_ids=self.tax_21)]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -31.5, 'balance':  -31.5},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  181.5, 'balance':  181.5},
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency':  -50.0, 'balance':  -50.0},
        ])

    def test_manual_tax_amount_kept_when_deleting_line_with_other_tax(self):
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
            self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_6),
        ])

        tax_line_21 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_21)
        invoice.line_ids = [Command.update(tax_line_21.id, {'amount_currency': -30.0})]
        invoice.invoice_line_ids = [Command.delete(invoice.invoice_line_ids[1].id)]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -30.0, 'balance':  -30.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  130.0, 'balance':  130.0},
        ])

    def test_manual_tax_amount_recomputed_when_deleting_line_with_same_tax(self):
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
            self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_21),
        ])

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -70.0})]
        invoice.invoice_line_ids = [Command.delete(invoice.invoice_line_ids[1].id)]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -21.0, 'balance':  -21.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  121.0, 'balance':  121.0},
        ])

    def test_manual_tax_amount_kept_when_changing_tax_of_line_with_other_tax(self):
        tax_12 = self.percent_tax(12.0)
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
            self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_6),
        ])

        tax_line_21 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_21)
        invoice.line_ids = [Command.update(tax_line_21.id, {'amount_currency': -30.0})]
        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids[1].id, {'tax_ids': [Command.set(tax_12.ids)]})]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -200.0, 'balance': -200.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -30.0, 'balance':  -30.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  354.0, 'balance':  354.0},
            {'display_type': 'tax',          'tax_line_id': tax_12.id,      'amount_currency':  -24.0, 'balance':  -24.0},
        ])

    def test_manual_tax_amount_recomputed_when_other_line_switches_to_same_tax(self):
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
            self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_6),
        ])

        tax_line_21 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_21)
        invoice.line_ids = [Command.update(tax_line_21.id, {'amount_currency': -30.0})]
        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids[1].id, {'tax_ids': [Command.set(self.tax_21.ids)]})]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -200.0, 'balance': -200.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -63.0, 'balance':  -63.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  363.0, 'balance':  363.0},
        ])

    def test_manual_tax_amount_kept_when_updating_label_of_its_base_line(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]
        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids.id, {'name': "new label"})]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -30.0, 'balance':  -30.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  130.0, 'balance':  130.0},
        ])

    def test_manual_tax_amount_kept_when_updating_line_feeding_other_tax_line_of_same_tax(self):
        tax_21_analytic = self.percent_tax(21.0, analytic=True)
        plan = self.env['account.analytic.plan'].create({'name': "Plan"})
        analytic_account_1, analytic_account_2 = self.env['account.analytic.account'].create([
            {'name': "Analytic 1", 'plan_id': plan.id},
            {'name': "Analytic 2", 'plan_id': plan.id},
        ])
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=tax_21_analytic, analytic_distribution={str(analytic_account_1.id): 100}),
            self._prepare_invoice_line(price_unit=200, tax_ids=tax_21_analytic, analytic_distribution={str(analytic_account_2.id): 100}),
        ])

        tax_line_1 = invoice.line_ids.filtered(lambda line: line.tax_line_id and line.analytic_distribution == {str(analytic_account_1.id): 100})
        invoice.line_ids = [Command.update(tax_line_1.id, {'amount_currency': -30.0})]
        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids[1].id, {'price_unit': 300})]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,              'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'product',      'tax_line_id': False,              'amount_currency': -300.0, 'balance': -300.0},
            {'display_type': 'tax',          'tax_line_id': tax_21_analytic.id, 'amount_currency':  -30.0, 'balance':  -30.0},
            {'display_type': 'tax',          'tax_line_id': tax_21_analytic.id, 'amount_currency':  -63.0, 'balance':  -63.0},
            {'display_type': 'payment_term', 'tax_line_id': False,              'amount_currency':  493.0, 'balance':  493.0},
        ])

    def test_manual_tax_amount_kept_when_updating_line_feeding_two_tax_lines(self):
        tax_recupel = self.fixed_tax(1.0, include_base_amount=True, sequence=0)
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=tax_recupel + self.tax_21),
            self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_6),
        ])

        tax_line_6 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_6)
        invoice.line_ids = [Command.update(tax_line_6.id, {'amount_currency': -30.0})]
        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids[0].id, {'price_unit': 200})]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -200.0,  'balance': -200.0},
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -200.0,  'balance': -200.0},
            {'display_type': 'tax',          'tax_line_id': tax_recupel.id, 'amount_currency':   -1.0,  'balance':   -1.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -42.21, 'balance':  -42.21},
            {'display_type': 'tax',          'tax_line_id': self.tax_6.id,  'amount_currency':  -30.0,  'balance':  -30.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  473.21, 'balance':  473.21},
        ])

    def test_manual_tax_amount_kept_in_foreign_currency_when_updating_line_with_other_tax(self):
        invoice = self._create_invoice(
            currency_id=self.eur,
            invoice_date='2017-01-01',
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
                self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_6),
            ],
        )

        tax_line_21 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_21)
        invoice.line_ids = [Command.update(tax_line_21.id, {'amount_currency': -30.0})]
        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids[1].id, {'price_unit': 300})]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance':  -50.0},
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -300.0, 'balance': -150.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -30.0, 'balance':  -15.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_6.id,  'amount_currency':  -18.0, 'balance':   -9.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  448.0, 'balance':  224.0},
        ])

    def test_manual_tax_amount_kept_in_refund_when_updating_line_with_other_tax(self):
        refund = self._create_invoice(
            move_type='out_refund',
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
                self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_6),
            ],
        )

        tax_line_21 = refund.line_ids.filtered(lambda line: line.tax_line_id == self.tax_21)
        refund.line_ids = [Command.update(tax_line_21.id, {'amount_currency': 30.0})]
        refund.invoice_line_ids = [Command.update(refund.invoice_line_ids[1].id, {'price_unit': 300})]

        self.assertRecordValues(refund.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency':  100.0, 'balance':  100.0},
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency':  300.0, 'balance':  300.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':   30.0, 'balance':   30.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_6.id,  'amount_currency':   18.0, 'balance':   18.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency': -448.0, 'balance': -448.0},
        ])

    def test_manual_tax_amount_kept_in_journal_entry_when_updating_line_with_other_tax(self):
        revenue = self.company_data['default_account_revenue']
        receivable = self.company_data['default_account_receivable']
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'line_ids': [
                Command.create({'account_id': revenue.id,    'balance': -100.0, 'tax_ids': [Command.set(self.tax_21.ids)]}),
                Command.create({'account_id': revenue.id,    'balance': -200.0, 'tax_ids': [Command.set(self.tax_6.ids)]}),
                Command.create({'account_id': receivable.id, 'balance':  333.0}),
            ],
        })
        base_line_6, receivable_line = move.line_ids[1:3]

        tax_line_21 = move.line_ids.filtered(lambda line: line.tax_line_id == self.tax_21)
        move.line_ids = [
            Command.update(tax_line_21.id,     {'balance': -30.0}),
            Command.update(receivable_line.id, {'balance': 342.0}),
        ]
        move.line_ids = [
            Command.update(base_line_6.id,     {'balance': -300.0}),
            Command.update(receivable_line.id, {'balance':  448.0}),
        ]

        self.assertRecordValues(move.line_ids, [
            {'display_type': 'product', 'tax_line_id': False,          'balance': -100.0},
            {'display_type': 'product', 'tax_line_id': False,          'balance': -300.0},
            {'display_type': 'product', 'tax_line_id': False,          'balance':  448.0},
            {'display_type': 'tax',     'tax_line_id': self.tax_21.id, 'balance':  -30.0},
            {'display_type': 'tax',     'tax_line_id': self.tax_6.id,  'balance':  -18.0},
        ])

    def test_manual_tax_amount_kept_when_changing_currency(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21, invoice_date='2017-01-01')

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]
        invoice.currency_id = self.eur

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -50.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -30.0, 'balance': -15.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  130.0, 'balance':  65.0},
        ])

    def test_manual_tax_amount_recomputed_when_changing_partner(self):
        other_partner = self.env['res.partner'].create({'name': "Other partner"})
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]
        invoice.partner_id = other_partner

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'partner_id': other_partner.id, 'amount_currency': -100.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'partner_id': other_partner.id, 'amount_currency':  -21.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'partner_id': other_partner.id, 'amount_currency':  121.0},
        ])

    def test_manual_tax_amount_kept_when_duplicating(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]
        copy = invoice.copy()

        self.assertRecordValues(copy.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -100.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -30.0, 'balance':  -30.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  130.0, 'balance':  130.0},
        ])

    def test_manual_tax_amount_untouched_when_editing_analytic_of_posted_invoice(self):
        tax_21_analytic = self.percent_tax(21.0, analytic=True)
        plan = self.env['account.analytic.plan'].create({'name': "Plan"})
        analytic_account = self.env['account.analytic.account'].create({'name': "Analytic", 'plan_id': plan.id})
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=tax_21_analytic)

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]
        invoice.action_post()
        invoice.invoice_line_ids.analytic_distribution = {str(analytic_account.id): 100}

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,              'amount_currency': -100.0},
            {'display_type': 'tax',          'tax_line_id': tax_21_analytic.id, 'amount_currency':  -30.0},
            {'display_type': 'payment_term', 'tax_line_id': False,              'amount_currency':  130.0},
        ])
        self.assertEqual(invoice.line_ids.filtered('tax_line_id'), tax_line)

    def test_manual_tax_amount_untouched_when_editing_analytic_of_posted_invoice(self):
        tax_21_analytic = self.percent_tax(21.0, analytic=True)
        plan = self.env['account.analytic.plan'].create({'name': "Plan"})
        analytic_account = self.env['account.analytic.account'].create({'name': "Analytic", 'plan_id': plan.id})
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=tax_21_analytic)

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]
        invoice.action_post()
        invoice.invoice_line_ids.analytic_distribution = {str(analytic_account.id): 100}

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,              'amount_currency': -100.0},
            {'display_type': 'tax',          'tax_line_id': tax_21_analytic.id, 'amount_currency':  -30.0},
            {'display_type': 'payment_term', 'tax_line_id': False,              'amount_currency':  130.0},
        ])
        self.assertEqual(invoice.line_ids.filtered('tax_line_id'), tax_line)

    def test_missing_tax_line_computed_when_creating_with_other_tax_line(self):
        reference = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)
        reference_tax_line = reference.line_ids.filtered('tax_line_id')
        invoice = self._create_invoice(line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
            self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_6),
            Command.create({
                'display_type': 'tax',
                'name': reference_tax_line.name,
                'tax_repartition_line_id': reference_tax_line.tax_repartition_line_id.id,
                'account_id': reference_tax_line.account_id.id,
                'amount_currency': -30.0,
            }),
        ])

        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -200.0},
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -30.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_6.id,  'amount_currency':  -12.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  342.0},
        ])

    def test_manual_tax_amount_kept_in_vendor_bill_when_updating_line_with_other_tax(self):
        tax_21_purchase = self.percent_tax(21.0, type_tax_use='purchase')
        tax_6_purchase = self.percent_tax(6.0, type_tax_use='purchase')
        bill = self._create_invoice(
            move_type='in_invoice',
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100, tax_ids=tax_21_purchase),
                self._prepare_invoice_line(price_unit=200, tax_ids=tax_6_purchase),
            ],
        )

        tax_line_21 = bill.line_ids.filtered(lambda line: line.tax_line_id == tax_21_purchase)
        bill.line_ids = [Command.update(tax_line_21.id, {'amount_currency': 30.0})]
        bill.invoice_line_ids = [Command.update(bill.invoice_line_ids[1].id, {'price_unit': 300})]

        self.assertRecordValues(bill.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,              'amount_currency':  100.0},
            {'display_type': 'product',      'tax_line_id': False,              'amount_currency':  300.0},
            {'display_type': 'tax',          'tax_line_id': tax_21_purchase.id, 'amount_currency':   30.0},
            {'display_type': 'tax',          'tax_line_id': tax_6_purchase.id,  'amount_currency':   18.0},
            {'display_type': 'payment_term', 'tax_line_id': False,              'amount_currency': -448.0},
        ])

    def test_manual_tax_amount_kept_when_reversing(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]
        refund = invoice._reverse_moves()

        self.assertRecordValues(refund.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency':  100.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency': -130.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':   30.0},
        ])

    def test_manual_price_included_tax_amount_kept_when_updating_line_with_other_tax(self):
        tax_21_included = self.percent_tax(21.0, price_include_override='tax_included')
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=121, tax_ids=tax_21_included),
            self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_6),
        ])

        tax_line_21 = invoice.line_ids.filtered(lambda line: line.tax_line_id == tax_21_included)
        invoice.line_ids = [Command.update(tax_line_21.id, {'amount_currency': -30.0})]
        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids[1].id, {'price_unit': 300})]

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,              'amount_currency': -100.0},
            {'display_type': 'product',      'tax_line_id': False,              'amount_currency': -300.0},
            {'display_type': 'tax',          'tax_line_id': tax_21_included.id, 'amount_currency':  -30.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_6.id,      'amount_currency':  -18.0},
            {'display_type': 'payment_term', 'tax_line_id': False,              'amount_currency':  448.0},
        ])

    def test_cash_rounding_biggest_tax_when_updating_line(self):
        cash_rounding = self.env['account.cash.rounding'].create({
            'name': "Biggest tax",
            'rounding': 0.05,
            'strategy': 'biggest_tax',
            'rounding_method': 'HALF-UP',
            'profit_account_id': self.company_data['default_account_revenue'].id,
            'loss_account_id': self.company_data['default_account_expense'].id,
        })
        invoice = self._create_invoice(
            invoice_cash_rounding_id=cash_rounding.id,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=10.03, tax_ids=self.tax_21),
                self._prepare_invoice_line(price_unit=20, tax_ids=self.tax_6),
            ],
        )

        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids[1].id, {'price_unit': 30})]

        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -30.0},
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -10.03},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -2.11},
            {'display_type': 'tax',          'tax_line_id': self.tax_6.id,  'amount_currency':  -1.8},
            {'display_type': 'rounding',     'tax_line_id': self.tax_21.id, 'amount_currency':  -0.01},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  43.95},
        ])

    def test_manual_tax_amount_kept_with_mixed_early_payment_discount_when_updating_line_with_other_tax(self):
        payment_term = self.env['account.payment.term'].create({
            'name': "10% early payment discount",
            'early_discount': True,
            'discount_percentage': 10,
            'discount_days': 10,
            'early_pay_discount_computation': 'mixed',
            'line_ids': [Command.create({'value': 'percent', 'nb_days': 0, 'value_amount': 100})],
        })
        invoice = self._create_invoice(
            invoice_payment_term_id=payment_term.id,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
                self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_6),
            ],
        )

        tax_line_21 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_21)
        invoice.line_ids = [Command.update(tax_line_21.id, {'amount_currency': -25.0})]
        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids[1].id, {'price_unit': 300})]

        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -300.0},
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0},
            {'display_type': 'epd',          'tax_line_id': False,          'amount_currency':  -40.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -25.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_6.id,  'amount_currency':  -16.2},
            {'display_type': 'epd',          'tax_line_id': False,          'amount_currency':   10.0},
            {'display_type': 'epd',          'tax_line_id': False,          'amount_currency':   30.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  441.2},
        ])

    def test_manual_tax_amount_kept_on_one_of_two_repartition_lines_when_updating_line_with_other_tax(self):
        other_tax_account = self.env['account.account'].create({'code': '451002', 'name': "Other tax account", 'account_type': 'liability_current'})
        tax_account = self.company_data['default_account_tax_sale']
        repartition_lines = [
            Command.create({'repartition_type': 'base'}),
            Command.create({'repartition_type': 'tax', 'factor_percent': 50, 'account_id': tax_account.id}),
            Command.create({'repartition_type': 'tax', 'factor_percent': 50, 'account_id': other_tax_account.id}),
        ]
        tax_21_split = self.percent_tax(21.0, invoice_repartition_line_ids=repartition_lines, refund_repartition_line_ids=repartition_lines)
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=tax_21_split),
            self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_6),
        ])

        tax_line_1 = invoice.line_ids.filtered(lambda line: line.tax_line_id == tax_21_split and line.account_id == tax_account)
        invoice.line_ids = [Command.update(tax_line_1.id, {'amount_currency': -15.0})]
        invoice.invoice_line_ids = [Command.update(invoice.invoice_line_ids[1].id, {'price_unit': 300})]

        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'display_type': 'product',      'tax_line_id': False,           'amount_currency': -300.0},
            {'display_type': 'product',      'tax_line_id': False,           'amount_currency': -100.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_6.id,   'amount_currency':  -18.0},
            {'display_type': 'tax',          'tax_line_id': tax_21_split.id, 'amount_currency':  -15.0},
            {'display_type': 'tax',          'tax_line_id': tax_21_split.id, 'amount_currency':  -10.5},
            {'display_type': 'payment_term', 'tax_line_id': False,           'amount_currency':  443.5},
        ])
        self.assertRecordValues(tax_line_1, [{'account_id': tax_account.id, 'amount_currency': -15.0}])

    def test_manual_tax_amount_recomputed_when_switching_to_refund(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]
        invoice.action_switch_move_type()

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency':  100.0},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency': -121.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':   21.0},
        ])

    def test_manual_tax_amount_recomputed_when_changing_tax_mode(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]
        invoice.document_tax_mode = 'tax_included'

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -82.64},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency': -17.36},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency': 100.0},
        ])

    def test_tax_lines_per_base_line(self):
        tax_recupel = self.fixed_tax(1.0, include_base_amount=True, sequence=0)
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
            self._prepare_invoice_line(price_unit=200, tax_ids=self.tax_6),
            self._prepare_invoice_line(price_unit=300, tax_ids=tax_recupel + self.tax_21),
            self._prepare_invoice_line(price_unit=400),
        ])
        line_21, line_6, line_recupel_21, line_untaxed = invoice.invoice_line_ids
        tax_line_21, tax_line_6, tax_line_recupel = (
            invoice.line_ids.filtered(lambda line: line.tax_line_id == tax)
            for tax in (self.tax_21, self.tax_6, tax_recupel)
        )

        self.assertEqual(invoice._get_tax_lines_per_base_line(), {
            line_21:         tax_line_21,
            line_6:          tax_line_6,
            line_recupel_21: tax_line_recupel + tax_line_21,
            line_untaxed:    self.env['account.move.line'],
        })

    def test_manual_tax_amount_kept_when_rate_changes(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21, currency_id=self.eur, invoice_date='2017-01-01')

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]
        invoice.invoice_date = '2018-01-02'

        self.assertRecordValues(invoice.line_ids, [
            {'display_type': 'product',      'tax_line_id': False,          'amount_currency': -100.0, 'balance': -25.0},
            {'display_type': 'tax',          'tax_line_id': self.tax_21.id, 'amount_currency':  -30.0, 'balance':  -7.5},
            {'display_type': 'payment_term', 'tax_line_id': False,          'amount_currency':  130.0, 'balance':  32.5},
        ])

    @freeze_time('2017-01-01')
    def test_manual_tax_amount_foreign_currency_flow(self):
        invoice = self._create_invoice_one_line(price_unit=100, tax_ids=self.tax_21)

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30})]

        self.assertRecordValues(invoice.line_ids, [
            {'amount_currency': -100.0},
            {'amount_currency': -30.0},
            {'amount_currency': 130.0},
        ])

        invoice.currency_id = self.eur

        self.assertRecordValues(invoice.line_ids, [
            {'amount_currency': -100.0, 'balance': -50.0},
            {'amount_currency': -30.0, 'balance': -15.0},
            {'amount_currency': 130.0, 'balance': 65.0},
        ])

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -30.0})]

        self.assertRecordValues(invoice.line_ids, [
            {'amount_currency': -100.0, 'balance': -50.0},
            {'amount_currency': -30.0, 'balance': -15.0},
            {'amount_currency': 130.0, 'balance': 65.0},
        ])

        invoice.invoice_date = '2018-01-02'

        self.assertRecordValues(invoice.line_ids, [
            {'amount_currency': -100.0, 'balance': -25.0},
            {'amount_currency': -30.0, 'balance': -7.5},
            {'amount_currency': 130.0, 'balance': 32.5},
        ])

    def test_manual_tax_amount_adding_removing_lines(self):
        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_6),
            self._prepare_invoice_line(price_unit=100),
        ])

        tax_line_6 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_6)
        tax_line_21 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_21)
        invoice.line_ids = [
            Command.update(tax_line_6.id, {'amount_currency': -10}),
            Command.update(tax_line_21.id, {'amount_currency': -30}),
        ]

        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100},
            {'amount_currency': -100},
            {'amount_currency': -100},
            {'amount_currency': -30},
            {'amount_currency': -10},
            {'amount_currency': 340},
        ])

        # Removing a base line not affecting the tax line should not trigger a recomputation.
        base_line = invoice.invoice_line_ids.filtered(lambda line: not line.tax_ids)
        invoice.line_ids = [Command.unlink(base_line.id)]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100},
            {'amount_currency': -100},
            {'amount_currency': -30},
            {'amount_currency': -10},
            {'amount_currency': 240},
        ])

        # Removing a base line affecting a specific tax line should only trigger the recomputation of that one.
        base_line = invoice.invoice_line_ids.filtered(lambda line: line.tax_ids == self.tax_6)
        invoice.line_ids = [Command.unlink(base_line.id)]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100},
            {'amount_currency': -30},
            {'amount_currency': 130},
        ])

        # Triggering the recomputation of the tax line but editing its amount at the same time should
        # keep the user input.
        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [
            self._prepare_invoice_line(price_unit=100, tax_ids=self.tax_21),
            Command.update(tax_line.id, {'amount_currency': -50}),
        ]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100},
            {'amount_currency': -100},
            {'amount_currency': -50},
            {'amount_currency': 250},
        ])

    def test_analytic_distribution_and_analytic_checkbox_on_taxes(self):
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Default'})
        anal_acc_a = self.env['account.analytic.account'].create({
            'name': 'anal_acc_a',
            'plan_id': analytic_plan.id,
        })
        anal_distr_a = {str(anal_acc_a.id): 100.0}
        anal_acc_b = self.env['account.analytic.account'].create({
            'name': 'anal_acc_b',
            'plan_id': analytic_plan.id,
        })
        anal_distr_b = {str(anal_acc_b.id): 100.0}
        anal_acc_c = self.env['account.analytic.account'].create({
            'name': 'anal_acc_c',
            'plan_id': analytic_plan.id,
        })
        anal_distr_c = {str(anal_acc_c.id): 100.0}

        invoice = self._create_invoice(invoice_line_ids=[
            self._prepare_invoice_line(price_unit=100, analytic_distribution=anal_distr_a, tax_ids=self.tax_21),
            self._prepare_invoice_line(price_unit=100, analytic_distribution=anal_distr_b, tax_ids=self.tax_21),
        ])
        # There are 2 tax lines because the repartition lines are not 'use_in_tax_closing'.
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_b},
            {'amount_currency': -21, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -21, 'analytic_distribution': anal_distr_b},
            {'amount_currency': 242, 'analytic_distribution': None},
        ])

        # All the tax lines should now be merged into one.
        self.tax_21.invoice_repartition_line_ids.use_in_tax_closing = True
        invoice.invoice_line_ids = [
            self._prepare_invoice_line(price_unit=100, analytic_distribution=anal_distr_c, tax_ids=self.tax_21),
        ]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_b},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_c},
            {'amount_currency': -63, 'analytic_distribution': None},
            {'amount_currency': 363, 'analytic_distribution': None},
        ])

        # Custom tax amount.
        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -70})]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_b},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_c},
            {'amount_currency': -70, 'analytic_distribution': None},
            {'amount_currency': 370, 'analytic_distribution': None},
        ])

        # Changing the analytic accounts should not recompute the tax line.
        base_line_b = invoice.invoice_line_ids.filtered(lambda line: line.analytic_distribution == anal_distr_b)
        base_line_c = invoice.invoice_line_ids.filtered(lambda line: line.analytic_distribution == anal_distr_c)
        invoice.line_ids = [
            Command.update(base_line_b.id, {'analytic_distribution': anal_distr_a}),
            Command.update(base_line_c.id, {'analytic_distribution': anal_distr_a}),
        ]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -70, 'analytic_distribution': None},
            {'amount_currency': 370, 'analytic_distribution': None},
        ])

        # Same with the 'analytic' ticked on the tax. This time, changing the analytic distribution
        # will impact the tax lines.
        self.tax_21.analytic = True
        invoice.line_ids = [
            Command.update(invoice.invoice_line_ids[0].id, {'analytic_distribution': anal_distr_a}),
            Command.update(invoice.invoice_line_ids[1].id, {'analytic_distribution': anal_distr_b}),
            Command.update(invoice.invoice_line_ids[2].id, {'analytic_distribution': anal_distr_c}),
        ]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_b},
            {'amount_currency': -100, 'analytic_distribution': anal_distr_c},
            {'amount_currency': -21, 'analytic_distribution': anal_distr_a},
            {'amount_currency': -21, 'analytic_distribution': anal_distr_b},
            {'amount_currency': -21, 'analytic_distribution': anal_distr_c},
            {'amount_currency': 363, 'analytic_distribution': None},
        ])

    @freeze_time('2017-01-01')
    def test_currency_rate_change_only(self):
        # Regression for the rate-only path inside _sync_tax_lines: when only the currency rate
        # changes, a manually-edited tax line keeps its 'amount_currency' and 'balance' is re-rated.
        invoice = self._create_invoice_one_line(
            price_unit=100,
            tax_ids=self.tax_21,
            currency_id=self.eur.id,
        )
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100.0, 'balance': -50.0},
            {'amount_currency': -21.0, 'balance': -10.5},
            {'amount_currency': 121.0, 'balance': 60.5},
        ])

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -19.0})]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100.0, 'balance': -50.0},
            {'amount_currency': -19.0, 'balance': -9.5},
            {'amount_currency': 119.0, 'balance': 59.5},
        ])

        invoice.invoice_date = '2018-01-02'
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -100.0, 'balance': -25.0},
            {'amount_currency': -19.0, 'balance': -4.75},
            {'amount_currency': 119.0, 'balance': 29.75},
        ])

    def test_python_tax_and_regular_tax_on_same_line(self):
        # Smoke test for the multi-tax bucketing path in _sync_tax_lines.track_base_lines_values:
        # a base line carrying both a python_tax (depends on the product) and a percent_tax
        # (does not) must bucket consistently across snapshots regardless of tax order, so a
        # neutral edit doesn't recompute manually-set tax amounts.
        self.ensure_installed('account_tax_python')
        py_tax = self.python_tax(formula="product.list_price * 0.1")

        invoice = self._create_invoice_one_line(
            price_unit=100,
            product_id=self.product_a.id,
            tax_ids=py_tax + self.tax_21,
        )

        py_tax_line = invoice.line_ids.filtered(lambda l: l.tax_line_id == py_tax)
        invoice.line_ids = [Command.update(py_tax_line.id, {'amount_currency': -7})]

        py_tax_line = invoice.line_ids.filtered(lambda l: l.tax_line_id == py_tax)
        self.assertEqual(py_tax_line.amount_currency, -7, "manual tax amount should be set")

        # Neutral edit: change the product label. Manual tax amount must survive.
        base_line = invoice.invoice_line_ids
        invoice.line_ids = [Command.update(base_line.id, {'name': 'renamed'})]

        py_tax_line = invoice.line_ids.filtered(lambda l: l.tax_line_id == py_tax)
        self.assertEqual(py_tax_line.amount_currency, -7, "manual tax amount must be preserved on neutral edit")

    def test_manual_tax_amount_preserved_on_analytic_change(self):
        # Test that a manually adjusted tax amount is preserved when
        # an unrelated field like analytic_distribution is modified.
        self.tax_21.invoice_repartition_line_ids.use_in_tax_closing = True
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Test Plan'})
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'Test Account',
            'plan_id': analytic_plan.id,
        })
        analytic_dist = {str(analytic_account.id): 100.0}

        invoice = self._create_invoice_one_line(
            price_unit=82.64,
            tax_ids=self.tax_21,
        )
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -82.64},
            {'amount_currency': -17.35},
            {'amount_currency': 99.99},
        ])

        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.line_ids = [Command.update(tax_line.id, {'amount_currency': -17.36})]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -82.64},
            {'amount_currency': -17.36},
            {'amount_currency': 100.00},
        ])

        base_line = invoice.invoice_line_ids
        invoice.line_ids = [Command.update(base_line.id, {'analytic_distribution': analytic_dist})]
        self.assertRecordValues(invoice.line_ids.sorted('amount_currency'), [
            {'amount_currency': -82.64, 'analytic_distribution': analytic_dist},
            {'amount_currency': -17.36, 'analytic_distribution': False},
            {'amount_currency': 100.00, 'analytic_distribution': False},
        ])

    def test_trust_precalculated_tax_lines_on_creation(self):
        """
        Test that when a move is created with explicitly provided tax lines and balances
        (like hr.expense does), the synchronization is skipped to prevent penny drift
        and preserve line ordering.
        """
        self.tax_21.analytic = False
        self.tax_21.invoice_repartition_line_ids.use_in_tax_closing = True

        move_vals = {
            'move_type': 'entry',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({
                    'account_id': self.company_data['default_account_revenue'].id,
                    'balance': -100.0,
                    'tax_ids': [Command.set(self.tax_21.ids)],
                }),
                Command.create({
                    'account_id': self.company_data['default_account_tax_sale'].id,
                    'balance': -21.01,  # Forced drifted penny
                    'tax_repartition_line_id': self.tax_21.invoice_repartition_line_ids.filtered(
                        lambda l: l.repartition_type == 'tax').id,
                }),
                Command.create({
                    'account_id': self.company_data['default_account_receivable'].id,
                    'balance': 121.01,
                }),
            ]
        }

        move = self.env['account.move'].create(move_vals)

        tax_line = move.line_ids.filtered('tax_repartition_line_id')
        self.assertEqual(tax_line.balance, -21.01, "The pre-calculated tax amount must be trusted on creation.")

    def test_trust_injected_tax_lines(self):
        """
        Test that when an external engine (like Avatax) injects a tax line into an
        existing move, Odoo hits the safety block instead of deleting and recalculating it.
        """
        self.tax_21.analytic = False
        self.tax_21.invoice_repartition_line_ids.use_in_tax_closing = True

        invoice = self._create_invoice_one_line(
            price_unit=800.0,
            tax_ids=self.env['account.tax'],  # Empty
        )

        # Simulate Avatax injecting a computed tax line
        invoice.write({
            'line_ids': [
                Command.create({
                    'display_type': 'tax',
                    'name': 'Injected External Tax',
                    'amount_currency': -96.0,
                    'tax_repartition_line_id': self.tax_21.invoice_repartition_line_ids.filtered(
                        lambda l: l.repartition_type == 'tax').id,
                    'account_id': self.company_data['default_account_tax_sale'].id,
                })
            ]
        })

        tax_line = invoice.line_ids.filtered('tax_repartition_line_id')
        self.assertEqual(tax_line.amount_currency, -96.0, "Injected tax lines must survive synchronization.")

    def test_injection_survives_subsequent_writes(self):
        """
        When an external API (like Avatax) calculates taxes, it injects them directly via write().
        Any subsequent, completely unrelated write will wake up the diffing engine. The engine will
        see the injected tax, assume it's an unprotected error, and recalculate it (or delete it).
        """
        self.tax_21.analytic = False

        invoice = self._create_invoice_one_line(
            price_unit=1000.0,
            tax_ids=self.env['account.tax'],  # Explicitly empty
        )

        tax_rep_line = self.tax_21.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax')

        invoice.write({
            'line_ids': [
                Command.create({
                    'display_type': 'tax',
                    'name': 'API Injected Tax',
                    'amount_currency': -123.45,
                    'tax_repartition_line_id': tax_rep_line.id,
                    'account_id': self.company_data['default_account_tax_sale'].id,
                })
            ]
        })

        # Confirm tax line is not recalculated
        tax_line = invoice.line_ids.filtered('tax_repartition_line_id')
        self.assertEqual(tax_line.amount_currency, -123.45, "Initial injection failed.")

        # Do unrelated write to invoice to make sure tax is not recalculated
        invoice.write({'payment_reference': 'API_PROCESSED_001'})
        tax_line_after = invoice.line_ids.filtered('tax_repartition_line_id')

        self.assertTrue(
            tax_line_after,
            "The API-injected tax was completely deleted by the diffing engine!"
        )
        self.assertEqual(
            tax_line_after.amount_currency,
            -123.45,
            "The API-injected tax amount was overwritten by the diffing engine!"
        )
