# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Onboarding(models.Model):
    _inherit = 'onboarding.onboarding'

    # Sale Quotation Onboarding
    @api.model
    def action_close_panel_sale_quotation(self):
        self.action_close_panel('sale.onboarding_onboarding_sale_quotation')
