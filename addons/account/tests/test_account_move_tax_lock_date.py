from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxBlockDate(AccountingTestCase):
    """
    Forbid creation, edition and deletion of Journal Items related to taxes with
    a date prior to the Tax Block Date.
    """

    def setUp(self):
        super(TestTaxBlockDate, self).setUp()
        self.user_id = self.env.user

        last_day_month = datetime.now()
        last_day_month = last_day_month.replace(day=monthrange(last_day_month.year, last_day_month.month)[1])
        self.last_day_month_str = last_day_month.strftime(DEFAULT_SERVER_DATE_FORMAT)
        first_day_month = datetime.now()
        first_day_month = first_day_month.replace(day=1)
        self.first_day_month_str = first_day_month.strftime(DEFAULT_SERVER_DATE_FORMAT)
        middle_day_month = datetime.now()
        middle_day_month = middle_day_month.replace(day=15)
        self.middle_day_month_str = middle_day_month.strftime(DEFAULT_SERVER_DATE_FORMAT)

        self.sale_journal_id = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)[0]
        self.account_id = self.env['account.account'].search([('internal_type', '=', 'receivable')], limit=1)[0]
        self.other_account_id = self.env['account.account'].search([('internal_type', '!=', 'receivable')], limit=1)[0]
        self.tax_id = self.env['account.tax'].search([], limit=1)[0]

        self.move = {
            'name': '/',
            'journal_id': self.sale_journal_id.id,
            'date': self.middle_day_month_str,
            'line_ids': [(0, 0, {
                    'name': 'foo',
                    'debit': 10,
                    'account_id': self.account_id.id,
                    'tax_ids': [(6, False, [self.tax_id.id])]
                }), (0, 0, {
                    'name': 'bar',
                    'credit': 10,
                    'account_id': self.account_id.id,
                })]
        }

    def test_create_before_block_date(self):
        """
        Checks that you cannot create an account.move with a date before the tax
        lock date
        """
        self.user_id.company_id.tax_lock_date = self.last_day_month_str
        with self.assertRaises(ValidationError):
            move = self.env['account.move'].create(self.move)
            move.post()

    def test_change_after_block_date(self):
        """
        Checks that you can change an account.move with a date after the tax
        lock date
        """
        self.user_id.company_id.tax_lock_date = self.first_day_month_str
        move = self.env['account.move'].create(self.move)
        move.line_ids[0].write({'account_id': self.other_account_id.id})
        move.line_ids[1].write({'account_id': self.other_account_id.id})
        move.line_ids[1].write({'debit': 11})
        move.line_ids[0].write({'credit': 11})
        move.post()
        move.line_ids[1].write({'tax_ids': [(5, False, False)]})

    def test_change_before_block_date(self):
        """
        Checks that you cannot change an account.move with a date before the tax
        lock date
        """
        self.user_id.company_id.tax_lock_date = self.first_day_month_str
        move = self.env['account.move'].create(self.move)
        self.user_id.company_id.tax_lock_date = self.last_day_month_str
        move.line_ids[0].write({'account_id': self.other_account_id.id})
        move.line_ids[1].write({'account_id': self.other_account_id.id})
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                move.line_ids[1].write({'debit': 11})
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                move.line_ids[1].write({'date': self.last_day_month_str, 'tax_ids': [(5, False, False)]})
        move.line_ids[0].write({'credit': 10})
        move.post()

    def test_unlink_before_block_date(self):
        """
        Checks that you cannot unlink an account.move with a date before the tax
        lock date
        """
        self.user_id.company_id.tax_lock_date = self.first_day_month_str
        move = self.env['account.move'].create(self.move)
        move.post()
        self.user_id.company_id.tax_lock_date = self.last_day_month_str
        with self.assertRaises(ValidationError):
            move.unlink()

    def test_unlink_after_block_date(self):
        """
        Checks that you can unlink an account.move with a date after the lock
        date
        """
        self.user_id.company_id.tax_lock_date = self.first_day_month_str
        move = self.env['account.move'].create(self.move)
        move.post()
        move.unlink()
