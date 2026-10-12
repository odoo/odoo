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
        cash_pm = cls.pos_config_usd._get_cash_payment_method()
        cls.cash_journal = cash_pm.journal_id
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
