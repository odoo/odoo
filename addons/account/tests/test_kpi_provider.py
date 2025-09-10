from odoo import Command
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestKpiProvider(TransactionCase):

    def test_kpi_summary(self):
        """
        - Ensure that nothing is reported when there is nothing to report
        - All <account.move> in draft or to_check should be reported
        - Posting one <account.move> should reduce the number reported
        - Posting all <account.move> of a journal_type should remove that journal_type from the reporting
        """
        # Clean things for the test
        self.env['account.move'].search([('state', '=', 'draft')]).unlink()
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [])

        company_id = self.ref('base.main_company')
        account_id = self.env['account.account'].search([('company_id', '=', company_id)], limit=1)
        base_move = {
            'company_id': company_id,
            'line_ids': [Command.create({'account_id': account_id.id, 'quantity': 15, 'price_unit': 10})],
            'partner_id': self.env.user.partner_id.id,
        }
        all_moves = self.env['account.move'].create(
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

        all_moves[0].action_post()
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [
            {'id': 'account_journal_type.general', 'name': 'Miscellaneous', 'type': 'integer', 'value': 1},
            {'id': 'account_journal_type.sale', 'name': 'Sales', 'type': 'integer', 'value': 14},
            {'id': 'account_journal_type.purchase', 'name': 'Purchase', 'type': 'integer', 'value': 19},
        ])

        all_moves[1].action_post()
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [
            {'id': 'account_journal_type.sale', 'name': 'Sales', 'type': 'integer', 'value': 14},
            {'id': 'account_journal_type.purchase', 'name': 'Purchase', 'type': 'integer', 'value': 19},
        ])

        all_moves[2].action_post()
        all_moves[2].to_check = True
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [
            {'id': 'account_journal_type.sale', 'name': 'Sales', 'type': 'integer', 'value': 14},
            {'id': 'account_journal_type.purchase', 'name': 'Purchase', 'type': 'integer', 'value': 19},
        ])

        all_moves[2].button_set_checked()
        self.assertCountEqual(self.env['kpi.provider'].get_account_kpi_summary(), [
            {'id': 'account_journal_type.sale', 'name': 'Sales', 'type': 'integer', 'value': 13},
            {'id': 'account_journal_type.purchase', 'name': 'Purchase', 'type': 'integer', 'value': 19},
        ])
