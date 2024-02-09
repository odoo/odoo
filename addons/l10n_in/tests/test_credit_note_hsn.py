from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import Command, fields
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestCreditNoteHSN(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="in"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.product_line_vals = {
            'product_id': cls.product_a.id,
            'l10n_in_hsn_code': '1234',
        }
        cls.company_data["company"].write({
            "state_id": cls.env.ref("base.state_in_ts").id,
        })
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'company_id': cls.company_data["company"].id,
            'date': fields.Date.today(),
            'invoice_line_ids': [Command.create(cls.product_line_vals)],
        })
        cls.invoice.action_post()

    def test_credit_note_hsn(self):
        refund_wizard = self.env['account.move.reversal'].with_context({'active_ids': [self.invoice.id], 'active_model': 'account.move'}).create({
            'reason': "no reason",
            'journal_id': self.invoice.journal_id.id,
        })
        res = refund_wizard.refund_moves()
        reverse_move = self.env['account.move'].browse(res['res_id'])
        account_move_hsn = self.invoice.invoice_line_ids.l10n_in_hsn_code
        account_move_reversal_hsn = reverse_move.invoice_line_ids.l10n_in_hsn_code
        self.assertEqual(account_move_hsn, '1234')
        self.assertEqual(account_move_hsn, account_move_reversal_hsn, "HSN code should be same in invoice line and credit note line")
