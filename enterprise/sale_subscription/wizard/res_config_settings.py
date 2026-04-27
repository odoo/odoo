# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_consolidation = fields.Boolean(
        string="Consolidate subscriptions billing",
        help="Consolidate all of a customer's subscriptions that are due to be billed on the same day onto a single invoice.",
        config_parameter='sale_subscription.invoice_consolidation',
    )
