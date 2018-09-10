# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Lead(models.Model):
    _inherit = 'crm.lead'

    def website_form_input_filter(self, request, values):
        defaults = self.default_get(['medium_id', 'team_id'])
        values['medium_id'] = (
                values.get('medium_id') or
                defaults.get('medium_id') or
                self.sudo().env['ir.model.data'].xmlid_to_res_id('utm.utm_medium_website')
        )

        values['team_id'] = values.get('team_id') or defaults.get('team_id')

        if not values['team_id']:
            team_model = self.env['ir.model'].search([('model', '=', 'crm.team')])
            lead_model = self.env['ir.model'].search([('model', '=', 'crm.lead')])

            values['team_id'] = self.env['mail.alias'].search([('alias_model_id', '=', lead_model.id),
                ('alias_parent_model_id', '=', team_model.id),
                ('alias_name', 'ilike', '%\web%')], limit=1).alias_parent_thread_id

        return values
