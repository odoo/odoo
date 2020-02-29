# -*- coding: utf-8 -*-

from odoo.addons.account.tests.common import AccountTestCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMoveRounding(AccountTestCommon):

    @classmethod
    def setUpClass(cls):
        super(TestAccountMoveRounding, cls).setUpClass()
        cls.currency = cls.env['res.currency'].create({
            'name': "RAM",
            'symbol': "🐏",
            'rounding': 0.01,
        })
        cls.company = cls.env['res.company'].create({
            'name': "SHEEP",
            'currency_id': cls.currency.id,
        })
        cls.account_type = cls.env['account.account.type'].create({
            'name': 'BAAH',
            'internal_group': 'asset',
            'type': 'receivable'
        })
        cls.journal = cls.env['account.journal'].create({
            'company_id': cls.company.id,
            'name': 'LAMB',
            'code': 'LL',
            'type': 'purchase',
        })
        cls.account = cls.env['account.account'].create({
            'company_id': cls.company.id,
            'name': 'EWE',
            'code': 'EE',
            'user_type_id': cls.account_type.id,
            'reconcile': True,
        })


    def test_move_line_rounding(self):
        """Whatever arguments we give to the creation of an account move,
        in every case the amounts should be properly rounded to the currency's precision.
        In other words, we don't fall victim of the limitation introduced by 9d87d15db6dd40

        Here the rounding should be done according to company_currency_id, which is a related
        on move_id.company_id.currency_id.
        In principle, it should not be necessary to add it to the create values,
        since it is supposed to be computed by the ORM...
        """
        move1 = self.env['account.move'].create({
            'journal_id': self.journal.id,
            'line_ids': [
                (0, 0, {'debit': 100.0 / 3, 'account_id': self.account.id}),
                (0, 0, {'credit': 100.0 / 3, 'account_id': self.account.id}),
            ],
        })
        move2 = self.env['account.move'].create({
            'journal_id': self.journal.id,
            'line_ids': [
                (0, 0, {'debit': 100.0 / 3, 'account_id': self.account.id,
                        'company_currency_id': self.company.currency_id.id}),
                (0, 0, {'credit': 100.0 / 3, 'account_id': self.account.id,
                        'company_currency_id': self.company.currency_id.id}),
            ],
        })

        self.assertEqual(
            [(33.33, 0.0), (0.0, 33.33)],
            move2.line_ids.mapped(lambda x: (x.debit, x.credit)),
            "Quantities should have been rounded according to the currency."
        )
        self.assertEqual(
            move1.line_ids.mapped(lambda x: (x.debit, x.credit)),
            move2.line_ids.mapped(lambda x: (x.debit, x.credit)),
            "In both cases the rounding should be correctly done."
        )
