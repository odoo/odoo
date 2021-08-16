import logging
import odoo.tests
import time
import requests
from odoo.addons.account.tests.test_reconciliation import TestReconciliation

_logger = logging.getLogger(__name__)


@odoo.tests.tagged('post_install', '-at_install')
@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUi(odoo.tests.HttpCase):

    def test_01_admin_bank_statement_reconciliation(self):
        bank_stmt_name = 'BNK/%s/0001' % time.strftime('%Y')
        bank_stmt_line = self.env['account.bank.statement'].search([('name', '=', bank_stmt_name)]).mapped('line_ids')
        if not bank_stmt_line:
            _logger.info("Tour bank_statement_reconciliation skipped: bank statement %s not found." % bank_stmt_name)
            return

        admin = self.env.ref('base.user_admin')

        # Tour can't be run if the setup if not the generic one.
        generic_coa = self.env.ref('l10n_generic_coa.configurable_chart_template', raise_if_not_found=False)
        if not admin.company_id.chart_template_id or admin.company_id.chart_template_id != generic_coa:
            _logger.info("Tour bank_statement_reconciliation skipped: generic coa not found.")
            return

        # To be able to test reconciliation, admin user must have access to accounting features, so we give him the right group for that
        admin.write({'groups_id': [(4, self.env.ref('account.group_account_user').id)]})

        payload = {'action':'bank_statement_reconciliation_view', 'statement_line_ids[]': bank_stmt_line.ids}
        prep = requests.models.PreparedRequest()
        prep.prepare_url(url="http://localhost/web#", params=payload)

        self.start_tour(prep.url.replace('http://localhost', '').replace('?', '#'),
            'bank_statement_reconciliation', login="admin")


@odoo.tests.tagged('post_install', '-at_install')
@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUiMultiCurrency(odoo.tests.HttpCase):
    def setUp(self):
        super(TestUiMultiCurrency, self).setUp()

        self.swiss_currency = self.env.ref("base.CHF")
        self.base_currency = self.env.ref("base.USD")
        self.base_company = self.env.ref('base.main_company')

        self.account_exchange = self.env.ref('l10n_generic_coa.income_currency_exchange')

        # create accounts and journal with swiss currency
        self.swiss_account_receivable = self.env['account.account'].create({
            'code': 'test 1000',
            'name': 'receivable swiss',
            'reconcile': True,
            'user_type_id': self.env.ref("account.data_account_type_receivable").id,
            'currency_id': self.swiss_currency.id,
        })
        self.swiss_account_payable = self.env['account.account'].create({
            'code': 'test 1001',
            'name': 'payable swiss',
            'reconcile': True,
            'user_type_id': self.env.ref("account.data_account_type_payable").id,
            'currency_id': self.swiss_currency.id,
        })
        self.swiss_account_bank = self.env['account.account'].create({
            'code': 'test 1002',
            'name': 'bank swiss',
            'reconcile': True,
            'user_type_id': self.env.ref("account.data_account_type_liquidity").id,
            'currency_id': self.swiss_currency.id,
        })
        self.swiss_account_income = self.env['account.account'].create({
            'code': 'test 1003',
            'name': 'income swiss',
            'reconcile': True,
            'user_type_id': self.env.ref("account.data_account_type_direct_costs").id,
            'currency_id': self.swiss_currency.id,
        })
        self.swiss_journal = self.env['account.journal'].create({
            'name': 'journal swiss',
            'type': 'sale',
            'code': 'INV_test',
            'currency_id': self.swiss_currency.id,
            'default_credit_account_id': self.swiss_account_bank.id,
            'default_debit_account_id': self.swiss_account_bank.id,
        })

        # create partner with swiss accounts
        self.swiss_partner = self.env['res.partner'].create({
            'name': 'test',
            'property_account_receivable_id': self.swiss_account_receivable.id,
            'property_account_payable_id': self.swiss_account_payable.id,
        })

    def test_01_admin_reconcile_multi_currency_writeoff_swiss_invoice_swiss_payment(self):
        # create an invoice in swiss currency
        invoice = self.env['account.move'].with_context(default_type='out_invoice').create({
            'type': 'out_invoice',
            'partner_id': self.swiss_partner.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'product that cost %s' % 100,
                'quantity': 1,
                'price_unit': 100,
                'account_id': self.swiss_account_income.id,
            })],
            'currency_id': self.swiss_currency.id,
            'journal_id': self.swiss_journal.id,
        })
        invoice.post()

        self.assertEqual(invoice.amount_total, 100.00)

        # create payment in swiss currency
        payment = self.env['account.payment'].create({
            'payment_date': time.strftime('%Y-%m-%d'),
            'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.swiss_partner.id,
            'amount': 50,
            'journal_id': self.swiss_journal.id,
            'currency_id': self.swiss_currency.id,
        })
        payment.post()

        # To be able to test reconciliation, admin user must have access to accounting features, so we give him the right group for that
        self.env.ref('base.user_admin').write({'groups_id': [(4, self.env.ref('account.group_account_user').id)]})

        self.swiss_journal.write({'name': 'journal test', 'type': 'general'}) # should be used by the tour
        self.swiss_account_bank.write({'name': 'bank test'}) # should be used by the tour

        last_line_id = self.env['account.move.line'].search([], order="id desc", limit=1).id

        # called by reconciliation js widget and add the write-off (see js test: "Manual Reconciliation currencies: create write-off")
        self.start_tour('/web#action=account.action_account_payments', 'payment_reconciliation', login="admin")

        # check move lines

        amount = self.swiss_currency._convert(50.0, self.base_currency, self.base_company, payment.payment_date)
        write_off_move_lines = self.env['account.move.line'].search([('id', '>=', last_line_id)])

        self.assertRecordValues(
            write_off_move_lines,
            [
                {
                    'account_id': self.swiss_account_bank.id,
                    'name': 'label test',
                    'currency_id': self.swiss_currency.id,
                    'amount_currency': 50.0,
                    'debit': amount,
                    'credit': 0.0,
                },
                {
                    'account_id': self.swiss_account_receivable.id,
                    'name': 'Write-Off',
                    'currency_id': self.swiss_currency.id,
                    'amount_currency': -50.0,
                    'debit': 0.0,
                    'credit': amount,
                },
                {
                    'account_id': self.swiss_account_bank.id,
                    'name': f'CUST.IN/{time.strftime("%Y")}/0001',
                    'currency_id': self.swiss_currency.id,
                    'amount_currency': 50.0,
                    'debit': amount,
                    'credit': 0.0,
                },
                {
                    'account_id': self.swiss_account_receivable.id,
                    'name': 'Currency exchange rate difference',
                    'currency_id': self.swiss_currency.id,
                    'amount_currency': 0.0,
                    'debit': 0.01,
                    'credit': 0.0,
                },
                {
                    'account_id': self.account_exchange.id,
                    'name': 'Currency exchange rate difference',
                    'currency_id': self.swiss_currency.id,
                    'amount_currency': 0.0,
                    'debit': 0.0,
                    'credit': 0.01,
                },
            ],
        )

    def test_02_admin_reconcile_multi_currency_writeoff_swiss_invoice_dollar_payment(self):
        # create partner, account and journal without currency
        partner = self.env['res.partner'].create({
            'name': 'test',
        })
        account_receivable = self.env.ref('l10n_generic_coa.receivable').id
        account_bank = self.env['account.account'].create({
            'code': 'test 1102',
            'name': 'bank test', # should be used by the tour
            'reconcile': True,
            'user_type_id': self.env.ref("account.data_account_type_liquidity").id,
        })
        journal = self.env['account.journal'].create({
            'name': 'journal test', # should be used by the tour
            'code': 'Bank Test',
            'type': 'general',
            'default_debit_account_id': account_bank.id,
            'default_credit_account_id': account_bank.id,
        })

        # create an invoice in swiss currency
        invoice = self.env['account.move'].with_context(default_type='out_invoice').create({
            'type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'product that cost %s' % 100,
                'quantity': 1,
                'price_unit': 100,
                'account_id': account_bank.id,
            })],
            'currency_id': self.swiss_currency.id,
            'journal_id': self.swiss_journal.id,
        })
        invoice.post()

        self.assertEqual(invoice.amount_total, 100.00)
        self.assertEqual(invoice.currency_id.id, self.swiss_currency.id)

        # create payment in dollar currency
        payment = self.env['account.payment'].create({
            'payment_date': time.strftime('%Y-%m-%d'),
            'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': partner.id,
            'amount': 50.0,
            'journal_id': journal.id,
            'currency_id': self.base_currency.id,
        })

        payment.post()

        # To be able to test reconciliation, admin user must have access to accounting features, so we give him the right group for that
        self.env.ref('base.user_admin').write({'groups_id': [(4, self.env.ref('account.group_account_user').id)]})

        last_line_id = self.env['account.move.line'].search([], order="id desc", limit=1).id

        # called by reconciliation js widget and add the write-off (see js test: "Manual Reconciliation currencies: create write-off")
        self.start_tour('/web#action=account.action_account_payments', 'payment_reconciliation', login="admin")

        # check move lines

        invoice_base_amount = self.swiss_currency._convert(100.0, self.base_currency, self.base_company, payment.payment_date)
        amount = invoice_base_amount - 50.0
        write_off_move_lines = self.env['account.move.line'].search([('id', '>=', last_line_id)])

        self.assertRecordValues(
            write_off_move_lines,
            [
                {
                    'account_id': account_receivable,
                    'name': 'Currency exchange rate difference',
                    'currency_id': self.swiss_currency.id,
                    'amount_currency': -0.01,
                    'debit': 0.0,
                    'credit': 0.0,
                },
                {
                    'account_id': self.account_exchange.id,
                    'name': 'Currency exchange rate difference',
                    'currency_id': self.swiss_currency.id,
                    'amount_currency': 0.01,
                    'debit': 0.0,
                    'credit': 0.0,
                },
                {
                    'account_id': account_bank.id,
                    'name': 'label test',
                    'currency_id': False,
                    'amount_currency': 0.0,
                    'debit': amount,
                    'credit': 0.0,
                },
                {
                    'account_id': account_receivable,
                    'name': 'Write-Off',
                    'currency_id': False,
                    'amount_currency': 0.0,
                    'debit': 0.0,
                    'credit': amount,
                },
                {
                    'account_id': journal.default_credit_account_id.id,
                    'name': f'CUST.IN/{time.strftime("%Y")}/0001',
                    'currency_id': False,
                    'amount_currency': 0.0,
                    'debit': 50.0,
                    'credit': 0.0,
                },
            ],
        )


@odoo.tests.tagged('post_install', '-at_install')
class TestReconciliationWidget(TestReconciliation):

    def test_statement_suggestion_other_currency(self):
        # company currency is EUR
        # payment in USD
        invoice = self.create_invoice(invoice_amount=50, currency_id=self.currency_usd_id)

        # journal currency in USD
        bank_stmt = self.acc_bank_stmt_model.create({
            'journal_id': self.bank_journal_usd.id,
            'date': time.strftime('%Y-07-15'),
            'name': 'payment %s' % invoice.name,
        })

        bank_stmt_line = self.acc_bank_stmt_line_model.create({'name': 'payment',
            'statement_id': bank_stmt.id,
            'partner_id': self.partner_agrolait_id,
            'amount': 50,
            'date': time.strftime('%Y-07-15'),
        })

        result = self.env['account.reconciliation.widget'].get_bank_statement_line_data(bank_stmt_line.ids)
        self.assertEqual(result['lines'][0]['reconciliation_proposition'][0]['amount_str'], '$ 50.00')

    def test_filter_partner1(self):
        inv1 = self.create_invoice(currency_id=self.currency_euro_id)
        inv2 = self.create_invoice(currency_id=self.currency_euro_id)
        partner = inv1.partner_id

        receivable1 = inv1.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
        receivable2 = inv2.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')

        bank_stmt = self.acc_bank_stmt_model.create({
            'company_id': self.env.ref('base.main_company').id,
            'journal_id': self.bank_journal_euro.id,
            'date': time.strftime('%Y-07-15'),
            'name': 'test',
        })

        bank_stmt_line = self.acc_bank_stmt_line_model.create({
            'name': 'testLine',
            'statement_id': bank_stmt.id,
            'amount': 100,
            'date': time.strftime('%Y-07-15'),
        })

        # This is like input a partner in the widget
        mv_lines_rec = self.env['account.reconciliation.widget'].get_move_lines_for_bank_statement_line(
            bank_stmt_line.id,
            partner_id=partner.id,
            excluded_ids=[],
            search_str=False,
            mode="rp",
        )
        mv_lines_ids = [l['id'] for l in mv_lines_rec]

        self.assertIn(receivable1.id, mv_lines_ids)
        self.assertIn(receivable2.id, mv_lines_ids)

        # With a partner set, type the invoice reference in the filter
        mv_lines_rec = self.env['account.reconciliation.widget'].get_move_lines_for_bank_statement_line(
            bank_stmt_line.id,
            partner_id=partner.id,
            excluded_ids=[],
            search_str=inv1.invoice_payment_ref,
            mode="rp",
        )
        mv_lines_ids = [l['id'] for l in mv_lines_rec]

        self.assertIn(receivable1.id, mv_lines_ids)
        self.assertNotIn(receivable2.id, mv_lines_ids)

        # Without a partner set, type "deco" in the filter
        mv_lines_rec = self.env['account.reconciliation.widget'].get_move_lines_for_bank_statement_line(
            bank_stmt_line.id,
            partner_id=False,
            excluded_ids=[],
            search_str="deco",
            mode="rp",
        )
        mv_lines_ids = [l['id'] for l in mv_lines_rec]

        self.assertIn(receivable1.id, mv_lines_ids)
        self.assertIn(receivable2.id, mv_lines_ids)

        # With a partner set, type "deco" in the filter and click on the first receivable
        mv_lines_rec = self.env['account.reconciliation.widget'].get_move_lines_for_bank_statement_line(
            bank_stmt_line.id,
            partner_id=partner.id,
            excluded_ids=[receivable1.id],
            search_str="deco",
            mode="rp",
        )
        mv_lines_ids = [l['id'] for l in mv_lines_rec]

        self.assertNotIn(receivable1.id, mv_lines_ids)
        self.assertIn(receivable2.id, mv_lines_ids)

    def test_partner_name_with_parent(self):
        parent_partner = self.env['res.partner'].create({
            'name': 'test',
        })
        child_partner = self.env['res.partner'].create({
            'name': 'test',
            'parent_id': parent_partner.id,
            'type': 'delivery',
        })
        self.create_invoice_partner(currency_id=self.currency_euro_id, partner_id=child_partner.id)

        bank_stmt = self.acc_bank_stmt_model.create({
            'company_id': self.env.ref('base.main_company').id,
            'journal_id': self.bank_journal_euro.id,
            'date': time.strftime('%Y-07-15'),
            'name': 'test',
        })

        bank_stmt_line = self.acc_bank_stmt_line_model.create({
            'name': 'testLine',
            'statement_id': bank_stmt.id,
            'amount': 100,
            'date': time.strftime('%Y-07-15'),
            'partner_name': 'test',
        })

        bkstmt_data = self.env['account.reconciliation.widget'].get_bank_statement_line_data(bank_stmt_line.ids)

        self.assertEqual(len(bkstmt_data['lines']), 1)
        self.assertEqual(bkstmt_data['lines'][0]['partner_id'], parent_partner.id)
