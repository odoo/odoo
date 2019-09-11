from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.exceptions import UserError
from datetime import date
from calendar import monthrange
# from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
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
        self.company = self.env.company
        company_id = self.company.id

        last_day_month = date.today()
        self.last_day_month = last_day_month.replace(day=monthrange(last_day_month.year, last_day_month.month)[1])
        first_day_month = date.today()
        self.first_day_month = first_day_month.replace(day=1)
        middle_day_month = date.today()
        middle_day_month = middle_day_month.replace(day=15)

        self.sale_journal_id = self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', company_id)], limit=1)[0]
        self.account_id = self.env['account.account'].search([('internal_type', '=', 'receivable'), ('company_id', '=', company_id)], limit=1)[0]
        self.other_account_id = self.env['account.account'].search([('internal_type', '!=', 'receivable'), ('company_id', '=', company_id)], limit=1)[0]
        self.tax_id = self.env['account.tax'].search([('company_id', '=', company_id)], limit=1)[0]

        self.move = {
            'name': '/',
            'journal_id': self.sale_journal_id.id,
            'date': middle_day_month,
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

        self.move_no_tax = {
            'name': '/',
            'journal_id': self.sale_journal_id.id,
            'date': middle_day_month,
            'line_ids': [(0, 0, {
                    'name': 'foo',
                    'debit': 10,
                    'account_id': self.account_id.id,
                }), (0, 0, {
                    'name': 'bar',
                    'credit': 10,
                    'account_id': self.account_id.id,
                })]
        }

    def test_tax_lock_date_post(self):
        """ Checks that it is impossible to post an entry
        before the tax lock date.
        """
        # Posting after the lock date is always allowed
        self.company.tax_lock_date = self.first_day_month
        # copy() because mail.thread modifies the dictionary given to create
        move_after_lock = self.env['account.move'].create(self.move.copy())
        move_after_lock.post()

        # Posting before the tax lock date is allowed only if the move doesn't contain any tax
        self.user_id.company_id.tax_lock_date = self.last_day_month
        move_before_lock_no_tax = self.env['account.move'].create(self.move_no_tax)
        move_before_lock_no_tax.post()

        # Posting before the tax lock date is not allowed for moves impacting the tax report
        self.user_id.company_id.tax_lock_date = self.last_day_month
        with self.assertRaises(UserError):
            self.env['account.move'].create(self.move.copy())

    def test_tax_lock_date_cancel(self):
        """ Checks that it is not possible to cancel an entry posted before the
        tax lock date if it impacts the tax report. """
        self.sale_journal_id.update_posted = True
        move = self.env['account.move'].create(self.move)
        move.post()
        move_no_tax = self.env['account.move'].create(self.move_no_tax)
        move_no_tax.post()

        self.user_id.company_id.tax_lock_date = self.last_day_month

        move_no_tax.button_cancel()
        with self.assertRaises(UserError):
            move.button_cancel()
