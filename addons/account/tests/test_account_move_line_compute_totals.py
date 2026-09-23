from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMoveLineComputeTotals(AccountTestInvoicingCommon):

    def test_cogs_line_totals_are_set(self):
        """ 'cogs' lines aren't part of the base lines _compute_totals gathers from
        _get_rounded_base_and_tax_lines() for the whole-invoice round_globally redistribution
        (that helper only gathers 'product' lines, plus a few other display types added on top
        of it), so they're still computed one line at a time instead.
        """
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'product line',
                    'quantity': 2,
                    'price_unit': 50.0,
                    'tax_ids': [],
                }),
                Command.create({
                    'name': 'cogs line',
                    'display_type': 'cogs',
                    'quantity': 1,
                    'price_unit': 30.0,
                    'tax_ids': [],
                }),
            ],
        })

        cogs_line = move.line_ids.filtered(lambda line: line.display_type == 'cogs')
        self.assertRecordValues(cogs_line, [{
            'price_subtotal': 30.0,
            'price_total': 30.0,
        }])
