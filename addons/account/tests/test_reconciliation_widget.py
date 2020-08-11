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
