from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import UserError


class AccountClosure(models.Model):
    _name = 'account.move.closure'

    company_id = fields.Many2one('res.company')
    date_closure = fields.Date()
    frequency = fields.Selection(selection=[('daily', 'Daily'), ('monthly', 'Monthly'), ('annually', 'Annually')])
    total_interval = fields.Monetary()
    grand_total_fiscal = fields.Monetary()
    total_beginning = fields.Monetary()
    sequence_id = fields.Many2one('ir.sequence')
    first_move_id = fields.Many2one('account.move')
    last_move_id = fields.Many2one('account.move')

    def _compute_total_interval(self):
        # do a search on am and compute sum(balance)
        return 0, first_move, last_move

    def _compute_grand_total_fiscal(self):
        # take previous object same frequency and compute sum(am.balance) + previous.amount
        return 0

    def _compute_total_beginning(self):
        # take previous object same frequency and compute sum(am.balance) + previous.amount
        return 0

    def write(self, vals):
        raise UserError()

    def unlink(self):
        raise UserError()

    def automated_closure(self, frequency='daily'):
        # To be executed by the CRON to compute all the amount
        # call every _compute to get the amounts
        computed_amounts = {}
        return self.create(computed_amounts)
