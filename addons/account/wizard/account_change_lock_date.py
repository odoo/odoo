from openerp import models, fields, api
from openerp.tools.translate import _

class AccountChangeLockDate(models.TransientModel):
    """
    This wizard is used to change the lock date
    """
    _name = 'account.change.lock.date'
    _description = 'Change lock date'

    period_lock_date = fields.Date(
        string='New lock date for non-advisers',
        default=lambda self: self.env.user.company_id.period_lock_date,
        required=True)
    fiscalyear_lock_date = fields.Date(
        string='New lock date',
        default=lambda self: self.env.user.company_id.fiscalyear_lock_date,
        required=True)

    @api.multi
    def change_lock_date(self):
        self.env.user.company_id.write({'period_lock_date': self.period_lock_date, 'fiscalyear_lock_date': self.fiscalyear_lock_date})
        return {'type': 'ir.actions.act_window_close'}
