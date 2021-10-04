# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    test_simulated_state = fields.Selection(
        string="Simulated State",
        help="The state in which transactions created from this token should be set.",
        selection=[
            ('pending', "Pending"),
            ('done', "Confirmed"),
            ('cancel', "Canceled"),
            ('error', "Error"),
        ],
    )
