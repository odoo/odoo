# -*- coding: utf-8 -*-

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMoveRounding(AccountTestInvoicingCommon):

    def test_move_line_rounding(self):
        """Whatever arguments we give to the creation of an account move,
        in every case the amounts should be properly rounded to the currency's precision.
        In other words, we don't fall victim of the limitation introduced by 9d87d15db6dd40

        Here the rounding should be done according to company_currency_id, which is a related
        on move_id.company_id.currency_id.
        In principle, it should not be necessary to add it to the create values,
        since it is supposed to be computed by the ORM...
        """
        move = self.env['account.move'].create({
            'line_ids': [
                (0, 0, {'debit': 100.0 / 3, 'account_id': self.company_data['default_account_revenue'].id}),
                (0, 0, {'credit': 100.0 / 3, 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })

        self.assertEqual(
            [(33.33, 0.0), (0.0, 33.33)],
            move.line_ids.mapped(lambda x: (x.debit, x.credit)),
            "Quantities should have been rounded according to the currency."
        )
