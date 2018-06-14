# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Lead(models.Model):
    _inherit = 'crm.lead'

    def website_form_input_filter(self, request, values):
        values['medium_id'] = values.get('medium_id') or \
                              self.default_get(['medium_id']).get('medium_id') or \
                              self.sudo().env.ref('utm.utm_medium_website').id
        values['team_id'] = values.get('team_id') or \
                            request.website.crm_default_team_id.id
        values['user_id'] = values.get('user_id') or \
                            request.website.crm_default_user_id.id
        return values


class Website(models.Model):
    _inherit = 'website'

    def _get_crm_default_team_domain(self):
        if self.env.user.has_group('crm.group_use_lead'):
            return [('use_leads', '=', True)]
        else:
            return [('use_opportunities', '=', True)]

    crm_default_team_id = fields.Many2one(
        'crm.team', string='Default Sales Teams',
        default=lambda self: self.env['crm.team'].search([], limit=1),
        domain=lambda self: self._get_crm_default_team_domain(),
        help='Default Sales Team for new leads created through the Contact Us form.')
    crm_default_user_id = fields.Many2one(
        'res.users', string='Default Salesperson', domain=[('share', '=', False)],
        help='Default salesperson for new leads created through the Contact Us form.')
