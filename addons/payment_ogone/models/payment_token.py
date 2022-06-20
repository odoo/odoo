# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class PaymentToken(models.Model):
    _inherit = 'payment.token'
