from odoo import fields, models
from odoo.exceptions import UserError


class AccountLockDateLog(models.Model):
    _name = "account.lock.date.log"
    _description = "Lock Date Change Log"
    _order = "write_date desc"

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
    )
    date_applied = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
    )
    lock_date_old = fields.Date()
    lock_date_new = fields.Date()
    note = fields.Text()

    def write(self, vals):
        if not self.env.user._is_admin():
            raise UserError("Lock date log entries cannot be modified.")
        return super().write(vals)

    def unlink(self):
        if not self.env.user._is_admin():
            raise UserError("Lock date log entries cannot be deleted.")
        return super().unlink()

