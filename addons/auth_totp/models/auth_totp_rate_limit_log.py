from odoo import fields, models


class AuthTotpRateLimitLog(models.TransientModel):
    _name = 'auth.totp.rate.limit.log'
    _description = 'TOTP rate limit logs'

    _user_id_limit_type_create_date_idx = models.Index("(user_id, limit_type, create_date)")

    user_id = fields.Many2one('res.users', required=True, readonly=True)
    ip = fields.Char(readonly=True)
    limit_type = fields.Selection([
        ('send_email', 'Send Email'),
        ('code_check', 'Code Checking'),
    ], readonly=True)
