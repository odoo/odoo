# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon

from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMovePartnerCount(AccountTestInvoicingCommon):

    def test_account_move_count(self):
        self.env['account.move'].create([
            {
                'type': 'out_invoice',
                'date': '2017-01-01',
                'invoice_date': '2017-01-01',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [(0, 0, {'name': 'aaaa', 'price_unit': 100.0})],
            },
            {
                'type': 'in_invoice',
                'date': '2017-01-01',
                'invoice_date': '2017-01-01',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [(0, 0, {'name': 'aaaa', 'price_unit': 100.0})],
            },
        ]).post()

        self.assertEqual(self.partner_a.supplier_rank, 1)
        self.assertEqual(self.partner_a.customer_rank, 1)
