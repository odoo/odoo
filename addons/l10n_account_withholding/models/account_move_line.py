# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # ------------------
    # Fields declaration
    # ------------------

    withholding_payment_id = fields.Boolean(
        comodel_name='account.payment',
        string="Withholding Payment",
        store=False,  # We only need it as inverse of the One2many computed & not stored on the payment
    )
