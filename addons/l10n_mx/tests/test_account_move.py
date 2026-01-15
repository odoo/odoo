from odoo.tests import tagged

from odoo import Command
from odoo.addons.l10n_mx.tests.common import TestMxCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountMove(TestMxCommon):

    def test_credit_note_assign_right_account_on_lines(self):
        """
        This test check if the lines of a credit note created for MX, reference the
        right account id by default.
        """
        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'company_id': self.company_data['company'].id,
            'partner_id': self.partner_mx.id,
            'invoice_line_ids': [Command.create({
                'name': 'Test',
                'quantity': 1,
                'price_unit': 100,
            })],
        })

        self.assertRecordValues(credit_note.line_ids, [
            {'display_type': 'product', 'account_code': '402.01.01'},
            {'display_type': 'payment_term', 'account_code': '105.01.01'},
        ])
