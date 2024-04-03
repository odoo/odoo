# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    website_sale_onboarding_payment_provider_state = fields.Selection([('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")], string="State of the website sale onboarding payment provider step", default='not_done')

    @api.model
    def action_open_website_sale_onboarding_payment_provider(self):
        """ Called by onboarding panel above the quotation list."""
        self.env.company.payment_onboarding_payment_method = 'stripe'
        menu_id = self.env.ref('website.menu_website_dashboard').id
        return self._run_payment_onboarding_step(menu_id)
