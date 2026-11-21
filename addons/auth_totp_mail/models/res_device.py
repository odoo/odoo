# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResSession(models.Model):
    _inherit = 'res.session'

    mfa_method = fields.Selection(selection_add=[('totp_mail', 'Email Code')])
