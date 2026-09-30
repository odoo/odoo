from odoo import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import CommonPosTest


@tagged('post_install', '-at_install')
class TestPosCashDifferenceTax(CommonPosTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pos_config_usd.cash_control = True
        cls.pos_config_usd.open_ui()
        cls.session = cls.pos_config_usd.current_session_id
        cls.cash_journal = cls.session.cash_journal_id
        cls.profit_account = cls.cash_journal.profit_account_id
        cls.tax_account = cls.env['account.account'].create({
            'name': 'Sales Tax',
            'code': 'TTAX',
            'account_type': 'liability_current',
        })
        cls.tax_included = cls._create_tax('tax_included')
        cls.tax_excluded = cls._create_tax('tax_excluded')

    @classmethod
    def _create_tax(cls, price_include_override):
        return cls.env['account.tax'].create({
            'name': f'Tax 25% {price_include_override}',
            'amount_type': 'percent',
            'amount': 25.0,
            'price_include_override': price_include_override,
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({'repartition_type': 'tax', 'account_id': cls.tax_account.id}),
            ],
        })

    def test_no_tax_on_counterpart(self):
        self.session._post_statement_difference(10)
        st_line = self.env['account.bank.statement.line'].search(
            [('pos_session_id', '=', self.session.id)], order='id desc', limit=1)
        self.assertRecordValues(st_line.move_id.line_ids, [
            {'balance': 10.0, 'account_id': self.cash_journal.default_account_id.id},
            {'balance': -10.0, 'account_id': self.profit_account.id},
        ])

    def test_tax_on_counterpart_splits_amount(self):
        # The tax is always treated as included, i.e. as part of the gross
        # counted difference, whatever the price_include configuration is.
        for tax in (self.tax_included, self.tax_excluded):
            with self.subTest(tax=tax.name):
                self.profit_account.tax_ids = [Command.set(tax.ids)]
                self.session._post_statement_difference(10)
                st_line = self.env['account.bank.statement.line'].search(
                    [('pos_session_id', '=', self.session.id)], order='id desc', limit=1)
                self.assertRecordValues(st_line.move_id.line_ids, [
                    {'balance': 10.0, 'account_id': self.cash_journal.default_account_id.id},
                    {'balance': -8.0, 'account_id': self.profit_account.id},
                    {'balance': -2.0, 'account_id': self.tax_account.id},
                ])
