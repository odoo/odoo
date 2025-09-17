from odoo import Command
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestKpiProvider(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Clean things for the test
        cls.env['account.move'].search([('state', '=', 'draft')]).unlink()

    def test_empty_kpi_summary(self):
        # Ensure that nothing gets reported when there is nothing to report
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [])

    def test_kpi_summary(self):
        company_id = self.ref('base.main_company')
        account_id = self.env['account.account'].search([('company_id', '=', company_id)], limit=1)
        base_move = {
            'company_id': company_id,
            'line_ids': [Command.create({'account_id': account_id.id, 'quantity': 15, 'price_unit': 10})],
            'partner_id': self.env.user.partner_id.id,
        }
        self.env['account.move'].create(
            [{**base_move, 'move_type': 'entry'}] * 2 +
            [{**base_move, 'move_type': 'out_invoice'}] * 3 +
            [{**base_move, 'move_type': 'out_refund'}] * 4 +
            [{**base_move, 'move_type': 'in_invoice'}] * 5 +
            [{**base_move, 'move_type': 'in_refund'}] * 6 +
            [{**base_move, 'move_type': 'out_receipt'}] * 7 +
            [{**base_move, 'move_type': 'in_receipt'}] * 8
        )
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [
            {'id': 'account_journal_type.general', 'name': 'Miscellaneous', 'type': 'integer', 'value': 2},
            {'id': 'account_journal_type.sale', 'name': 'Sales', 'type': 'integer', 'value': 3 + 4 + 7},
            {'id': 'account_journal_type.purchase', 'name': 'Purchase', 'type': 'integer', 'value': 5 + 6 + 8},
        ])

    def test_kpi_summary_doesnt_report_posted_moves(self):
        company_id = self.ref('base.main_company')
        account_id = self.env['account.account'].search([('company_id', '=', company_id)], limit=1).id
        move = self.env['account.move'].create({
            'company_id': company_id,
            'line_ids': [Command.create({'account_id': account_id, 'quantity': 15, 'price_unit': 10})],
            'partner_id': self.env.user.partner_id.id,
            'move_type': 'out_invoice',
        })
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [
            {'id': 'account_journal_type.sale', 'name': 'Sales', 'type': 'integer', 'value': 1},
        ])

        move.action_post()
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [])

    def test_kpi_summary_reports_posted_but_to_check_moves(self):
        company_id = self.ref('base.main_company')
        account_id = self.env['account.account'].search([('company_id', '=', company_id)], limit=1).id
        move = self.env['account.move'].create({
            'company_id': company_id,
            'line_ids': [Command.create({'account_id': account_id, 'quantity': 15, 'price_unit': 10})],
            'partner_id': self.env.user.partner_id.id,
            'move_type': 'out_invoice',
        })
        move.action_post()
        move.to_check = True
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [
            {'id': 'account_journal_type.sale', 'name': 'Sales', 'type': 'integer', 'value': 1},
        ])

        move.button_set_checked()
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [])
