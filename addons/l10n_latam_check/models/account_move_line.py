from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    latam_check_id = fields.Many2one('account.payment.latam.check')
