# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    website_sale_onboarding_payment_acquirer_done =\
        fields.Boolean("Website sale onboarding payment acquirer step done", default=False)

    @api.model
    def action_open_website_sale_onboarding_payment_acquirer(self):
        """ Called by onboarding panel above the quotation list."""
        action = self.env.ref('website_sale.action_open_website_sale_onboarding_payment_acquirer_wizard').read()[0]
        return action
