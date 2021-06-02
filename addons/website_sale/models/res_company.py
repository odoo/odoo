# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    website_sale_onboarding_payment_acquirer_state = fields.Selection([('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")], string="State of the website sale onboarding payment acquirer step", default='not_done')

    @api.model
    def action_open_website_sale_onboarding_payment_acquirer(self):
        """ Called by onboarding panel above the quotation list."""
        self.env.company.get_chart_of_accounts_or_fail()
        action = self.env.ref('website_sale.action_open_website_sale_onboarding_payment_acquirer_wizard').read()[0]
        return action
