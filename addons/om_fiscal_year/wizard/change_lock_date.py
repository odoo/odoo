from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError


class ChangeLockDate(models.TransientModel):
    _name = 'change.lock.date'
    _description = 'Change Lock Date'

    @api.model
    def default_get(self, vals):
        res = super(ChangeLockDate, self).default_get(vals)
        company_rec = self.env.user.company_id
        res.update({
            'company_id': company_rec.id,
            'period_lock_date': company_rec.period_lock_date,
            'fiscalyear_lock_date': company_rec.fiscalyear_lock_date,
            'tax_lock_date': company_rec.tax_lock_date,
        })
        return res

    company_id = fields.Many2one('res.company', string="Company",
                                 required=True, default=lambda self: self.env.user.company_id)
    period_lock_date = fields.Date(string='Journal Entries Lock Date',
                                   default=lambda self: self.env.user.company_id.period_lock_date,
                                   help='Prevent posting of journal entries in this period.')
    fiscalyear_lock_date = fields.Date(string='Lock Date for All Users',
                                       default=lambda self: self.env.user.company_id.fiscalyear_lock_date,
                                       help='No users, including Advisers, can edit accounts prior to and inclusive of '
                                            'this date. Use it for fiscal year locking.')
    tax_lock_date = fields.Date("Tax Lock Date", help="No users can edit journal entries related to a tax prior "
                                                      "and inclusive of this date.")

    def update_lock_date(self):
        self.ensure_one()
        has_manager_group = self.env.user.has_group('account.group_account_manager')
        if not (has_manager_group or self.env.uid == SUPERUSER_ID):
            raise UserError(_("You Are Not Allowed To Perform This Operation"))
        self.company_id.sudo().write({
            'period_lock_date': self.period_lock_date,
            'fiscalyear_lock_date': self.fiscalyear_lock_date,
            'tax_lock_date': self.tax_lock_date,
        })
