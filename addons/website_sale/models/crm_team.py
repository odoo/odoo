# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields, models, _


class CrmTeam(models.Model):
    _inherit = "crm.team"

    website_ids = fields.One2many('website', 'salesteam_id', string='Websites', help="Websites using this sales channel")
    abandoned_carts_count = fields.Integer(
        compute='_compute_abandoned_carts',
        string='Number of transactions to capture', readonly=True)
    abandoned_carts_amount = fields.Integer(
        compute='_compute_abandoned_carts',
        string='Amount of transactions to capture', readonly=True)

    def _compute_abandoned_carts(self):
        website_teams = self.filtered(lambda team: team.team_type == 'website')
        # abandoned carts are draft sales orders that have no order lines, a partner other than the public user, and created over an hour ago
        abandoned_carts_data = self.env['sale.order'].read_group([
            ('team_id', 'in', website_teams.ids),
            ('date_order', '<', fields.Datetime.to_string(datetime.now() - relativedelta(hours=1))),
            ('state', '=', 'draft'),
            ('partner_id', '!=', self.env.ref('base.public_user').id),
            ('order_line', '!=', False),
        ], ['amount_total', 'team_id'], ['team_id'])
        counts = dict((data['team_id'][0], data['team_id_count']) for data in abandoned_carts_data)
        amounts = dict((data['team_id'][0], data['amount_total']) for data in abandoned_carts_data)
        for team in website_teams:
            team.abandoned_carts_count = counts.get(team.id, 0)
            team.abandoned_carts_amount = amounts.get(team.id, 0)

    def _compute_dashboard_button_name(self):
        website_teams = self.filtered(lambda team: team.team_type == 'website' and not team.use_quotations)
        website_teams.update({'dashboard_button_name': _("Online Sales")})
        super(CrmTeam, self - website_teams)._compute_dashboard_button_name()
