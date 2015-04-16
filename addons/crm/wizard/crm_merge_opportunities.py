# -*- coding: utf-8 -*-

from openerp import api, fields, models

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

    opportunity_ids = fields.Many2many(comodel_name = 'crm.lead', relation='merge_opportunity_rel', column1='merge_id', column2='opportunity_id', string='Leads/Opportunities')
    user_id = fields.Many2one('res.users', string='Salesperson', index=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', index=True)

    @api.model
    def default_get(self, fields):
        """
        Use active_ids from the context to fetch the leads/opps to merge.
        In order to get merged, these leads/opps can't be in 'Dead' or 'Closed'
        """
        record_ids = self.env.context.get('active_ids')
        res = super(CrmMergeOpportunity, self).default_get(fields)
        if record_ids:
            opp_ids = []
            opps = self.env['crm.lead'].browse(record_ids)
            for opp in opps:
                if opp.probability < 100:
                    opp_ids.append(opp.id)
            if 'opportunity_ids' in fields:
                res['opportunity_ids'] = opp_ids
        return res

    @api.onchange('user_id')
    def on_change_user(self):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of. """
        team_id = False
        if self.user_id:
            if self.team_id:
                user_in_team = self.env['crm.team'].search([('id', '=', self.team_id.id), '|', ('user_id', '=', self.user_id.id), ('member_ids', '=', self.user_id.id)], count=True)
            else:
                user_in_team = False
            if not user_in_team:
                team_id = self.env['crm.team'].search(['|', ('user_id', '=', self.user_id.id), ('member_ids', '=', self.user_id.id)], limit=1).id
        self.team_id = team_id

    @api.multi
    def action_merge(self):
        self.ensure_one()
        opportunity2merge_ids = self.opportunity_ids
        #TODO: why is this passed through the context ?
        merge_result = self.with_context(lead_ids = [opportunity2merge_ids[0].id]).opportunity_ids.merge_opportunity(self.user_id.id, self.team_id.id)
        # The newly created lead might be a lead or an opp: redirect toward the right view
        if merge_result.type == 'opportunity':
            return merge_result.redirect_opportunity_view()
        else:
            return merge_result.redirect_lead_view()
