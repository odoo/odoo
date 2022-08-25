from odoo import fields, models


class AuthTotpRateLimitLog(models.TransientModel):
    _name = 'auth.totp.rate.limit.log'
    _description = 'TOTP rate limit logs'

    def init(self):
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS auth_totp_rate_limit_log_user_id_limit_type_create_date_idx
            ON auth_totp_rate_limit_log(user_id, limit_type, create_date);
        """)

    user_id = fields.Many2one('res.users', required=True, readonly=True)
    scope = fields.Char(readonly=True)
    ip = fields.Char(readonly=True)
    limit_type = fields.Selection([
        ('send_email', 'Send Email'),
        ('code_check', 'Code Checking'),
    ], readonly=True)
