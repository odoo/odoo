# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMovePartnerCount(AccountTestInvoicingCommon):

    def test_account_move_count(self):
        self.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'date': '2017-01-01',
                'invoice_date': '2017-01-01',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [(0, 0, {'name': 'aaaa', 'price_unit': 100.0})],
            },
            {
                'move_type': 'in_invoice',
                'date': '2017-01-01',
                'invoice_date': '2017-01-01',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [(0, 0, {'name': 'aaaa', 'price_unit': 100.0})],
            },
        ]).action_post()

        self.assertEqual(self.partner_a.supplier_rank, 1)
        self.assertEqual(self.partner_a.customer_rank, 1)
