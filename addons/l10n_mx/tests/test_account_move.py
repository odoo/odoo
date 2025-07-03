from odoo.tests import tagged

from odoo import Command
from odoo.addons.l10n_mx.tests.common import TestMxCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountMove(TestMxCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_credit_note_assign_right_account_on_lines(self):
        """
        This test check if the lines of a credit note created for MX, reference the
        right account id by default.
        """
        partner_mx = self.env['res.partner'].create({
            'name': 'Partner MX',
            'country_id': self.env.ref('base.mx').id,
        })
        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'company_id': self.company_data['company'].id,
            'partner_id': partner_mx.id,
            'invoice_line_ids': [Command.create({
                'name': 'Test',
                'quantity': 1,
                'price_unit': 100,
            })],
        })

        for line in credit_note.line_ids.filtered(lambda l: l.display_type == 'product'):
            self.assertEqual(line.account_id.code, '402.01.01')
