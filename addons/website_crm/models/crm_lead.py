# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Lead(models.Model):
    _inherit = 'crm.lead'

    def website_form_input_filter(self, request, values):
        values['medium_id'] = (
                values.get('medium_id') or
                self.default_get(['medium_id']).get('medium_id') or
                self.sudo().env['ir.model.data'].xmlid_to_res_id('utm.utm_medium_website')
        )
        return values
