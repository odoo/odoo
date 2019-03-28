# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MergeOpportunity(models.TransientModel):
    """
        Merge opportunities together.
        If we're talking about opportunities, it's just because it makes more sense
        to merge opps than leads, because the leads are more ephemeral objects.
        But since opportunities are leads, it's also possible to merge leads
        together (resulting in a new lead), or leads and opps together (resulting
        in a new opp).
    """

    _name = 'crm.merge.opportunity'
    _description = 'Merge Opportunities'

    @api.model
    def default_get(self, fields):
        """ Use active_ids from the context to fetch the leads/opps to merge.
            In order to get merged, these leads/opps can't be in 'Dead' or 'Closed'
        """
        record_ids = self._context.get('active_ids')
        result = super(MergeOpportunity, self).default_get(fields)

        if record_ids:
            if 'opportunity_ids' in fields:
                opp_ids = self.env['crm.lead'].browse(record_ids).filtered(lambda opp: opp.probability < 100).ids
                result['opportunity_ids'] = opp_ids

        return result

    opportunity_ids = fields.Many2many('crm.lead', 'merge_opportunity_rel', 'merge_id', 'opportunity_id', string='Leads/Opportunities')
    user_id = fields.Many2one('res.users', 'Salesperson', index=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', index=True)

    def action_merge(self):
        self.ensure_one()
        merge_opportunity = self.opportunity_ids.merge_opportunity(self.user_id.id, self.team_id.id)
        return merge_opportunity.redirect_lead_opportunity_view()

    @api.onchange('user_id')
    def _onchange_user(self):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of. """
        team_id = False
        if self.user_id:
            user_in_team = False
            if self.team_id:
                user_in_team = self.env['crm.team'].search_count([('id', '=', self.team_id.id), '|', ('user_id', '=', self.user_id.id), ('member_ids', '=', self.user_id.id)])
            if not user_in_team:
                team_id = self.env['crm.team'].search(['|', ('user_id', '=', self.user_id.id), ('member_ids', '=', self.user_id.id)], limit=1)
        self.team_id = team_id
