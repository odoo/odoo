# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Default subscription parameters
    subscription_default_plan_id = fields.Many2one(related='company_id.subscription_default_plan_id',
                                                         readonly=False)

    invoice_consolidation = fields.Boolean(
        string="Consolidate subscriptions billing",
        help="Consolidate all of a customer's subscriptions that are due to be billed on the same day onto a single invoice.",
        config_parameter='sale_subscription.invoice_consolidation',
    )
