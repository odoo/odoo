# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CrmMergeOpportunity(models.TransientModel):
    """
    Merge opportunities together.
    If we're talking about opportunities, it's just because it makes more sense
    to merge opps than leads, because the leads are more ephemeral objects.
    But since opportunities are leads, it's also possible to merge leads
    together (resulting in a new lead), or leads and opps together (resulting
    in a new opp).
    """

    _name = 'crm.merge.opportunity'
    _description = 'Merge opportunities'

    opportunity_ids = fields.Many2many('crm.lead', rel='merge_opportunity_rel', id1='merge_id', id2='opportunity_id', string='Leads/Opportunities')
    user_id = fields.Many2one('res.users', string='Salesperson', index=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id', index=True)

    @api.multi
    def action_merge(self):
        self.ensure_one()
        opportunities2merge = self.opportunity_ids

        #TODO: why is this passed through the context ?
        merge_id = opportunities2merge.with_context(lead_ids=[opportunities2merge[0].id]).merge_opportunity(self.user_id.id, self.team_id.id)

        # The newly created lead might be a lead or an opp: redirect toward the right view
        merge_result = self.env['crm.lead'].browse(merge_id)

        if merge_result.type == 'opportunity':
            return merge_result.redirect_opportunity_view()
        return merge_result.redirect_lead_view()

    @api.model
    def default_get(self, fields):
        """
        Use active_ids from the context to fetch the leads/opps to merge.
        In order to get merged, these leads/opps can't be in 'Dead' or 'Closed'
        """
        record_ids = self.env.context.get('active_ids')
        res = super(CrmMergeOpportunity, self).default_get(fields)

        if record_ids:
            opps = self.env['crm.lead'].browse(record_ids)
            opp_ids = opps.filtered(lambda o: o.probability < 100).ids
            if 'opportunity_ids' in fields:
                res['opportunity_ids'] = opp_ids

        return res

    @api.onchange('user_id')
    def _onchange_user_id(self):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of. """
        user_id = self.user_id.id
        if user_id:
            CrmTeam = self.env['crm.team']
            user_in_team = False
            team_id = self.team_id.id
            if team_id:
                user_in_team = CrmTeam.search_count([('id', '=', team_id), '|', ('user_id', '=', user_id), ('member_ids', '=', user_id)])
            if not user_in_team:
                self.team_id = CrmTeam.search(['|', ('user_id', '=', user_id), ('member_ids', '=', user_id)], limit=1)
