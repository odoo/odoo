# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _get_crm_default_team_domain(self):
        if not self.env.user.has_group('crm.group_use_lead'):
            return [('use_opportunities', '=', True)]
        return []

    crm_default_team_id = fields.Many2one(
        'crm.team', string='Default Sales Team', related='website_id.crm_default_team_id', readonly=False,
        domain=lambda self: self._get_crm_default_team_domain(),
        help='Default Sales Team for new leads created through the Contact Us form.')
    crm_default_user_id = fields.Many2one(
        'res.users', string='Default Salesperson', related='website_id.crm_default_user_id', domain=[('share', '=', False)], readonly=False,
        help='Default salesperson for new leads created through the Contact Us form.')
