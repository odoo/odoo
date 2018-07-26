from openerp.addons.account.tests.account_test_classes import AccountingTestCase
from openerp.osv.orm import except_orm
from datetime import datetime
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

class TestPeriodState(AccountingTestCase):
    """
    Forbid creation of Journal Entries for a closed period.
    """

    def setUp(self):
        super(TestPeriodState, self).setUp()
        self.user_id = self.env['res.users'].browse(self.uid)

        last_day_month = datetime.now() - relativedelta(months=1)
        last_day_month = last_day_month.replace(day=monthrange(last_day_month.year, last_day_month.month)[1])
        self.last_day_month_str = last_day_month.strftime(DEFAULT_SERVER_DATE_FORMAT)

        #make sure there is no unposted entry
        draft_entries = self.env['account.move'].search([('date', '<=', self.last_day_month_str), ('state', '=', 'draft')])
        if draft_entries:
            draft_entries.post()
        self.user_id.company_id.fiscalyear_lock_date = self.last_day_month_str
        self.sale_journal_id = self.env['account.journal'].search([('type', '=', 'sale')])[0]
        self.account_id = self.env['account.account'].search([('internal_type', '=', 'receivable')])[0]

    def test_period_state(self):
        with self.assertRaises(except_orm):
            move = self.env['account.move'].create({
                'name': '/',
                'journal_id': self.sale_journal_id.id,
                'date': self.last_day_month_str,
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
