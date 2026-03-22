from odoo import fields, models


class BrLockDateLog(models.Model):
    _name = "br.lock.date.log"
    _description = "Log de Alteracao de Lock Date"
    _order = "timestamp desc"

    # ref: public_sector/gov_account_lock_date_update/models/account_lock_date_log.py
    company_id = fields.Many2one("res.company", required=True, ondelete="cascade")
    user_id = fields.Many2one("res.users", required=True, ondelete="restrict")
    date_old = fields.Date()
    date_new = fields.Date()
    reason = fields.Text()
    timestamp = fields.Datetime(default=fields.Datetime.now, required=True)

