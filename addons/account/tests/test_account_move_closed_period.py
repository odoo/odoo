from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.osv.orm import except_orm
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

class TestPeriodState(AccountingTestCase):
    """
    Forbid creation of Journal Entries for a closed period.
    """

    def setUp(self):
        super(TestPeriodState, self).setUp()
        self.day_before_yesterday = datetime.now() - timedelta(2)
        self.yesterday = datetime.now() - timedelta(1)
        self.user_id = self.env.user
        self.user_id.company_id.write({'fiscalyear_lock_date': self.yesterday.strftime(DEFAULT_SERVER_DATE_FORMAT)})
        self.sale_journal_id = self.env['account.journal'].search([('type', '=', 'sale')])[0]
        self.account_id = self.env['account.account'].search([('internal_type', '=', 'receivable')])[0]

    def test_period_state(self):
        with self.assertRaises(except_orm):
            move = self.env['account.move'].create({
                'name': '/',
                'journal_id': self.sale_journal_id.id,
                'date': self.day_before_yesterday.strftime(DEFAULT_SERVER_DATE_FORMAT),
                'line_ids': [(0, 0, {
                        'name': 'foo',
                        'debit': 10,
                        'account_id': self.account_id.id,
                    }), (0, 0, {
                        'name': 'bar',
                        'credit': 10,
                        'account_id': self.account_id.id,
                    })]
            })
            move.post()
