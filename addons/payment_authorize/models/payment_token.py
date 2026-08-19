# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    authorize_profile = fields.Char(
        string="Authorize.Net Profile ID",
        help="The unique reference for the partner/token combination in the Authorize.net backend.")
