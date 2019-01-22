# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CommonMergeOpportunity(models.TransientModel):
    """
        Merge opportunities together.
        If we're talking about opportunities, it's just because it makes more sense
        to merge opps than leads, because the leads are more ephemeral objects.
        But since opportunities are leads, it's also possible to merge leads
        together (resulting in a new lead), or leads and opps together (resulting
        in a new opp).
    """

    _name = 'crm.common.merge.opportunity'
    _description = 'Common Merge Opportunities'

    @api.model
    def default_get(self, fields):
        default = super(CommonMergeOpportunity, self).default_get(fields)

        if self._context.get('active_model') != 'crm.lead':
            raise UserError(_("You can only apply this action from a lead."))

        lead = self.env['crm.lead'].browse(self.env.context.get('active_id'))
        default['lead_id'] = self.env.context.get('active_id')
        default['company_id'] = lead.company_id.id
        default['opportunity_ids'] = [self.env.context.get('active_id')]
        return default

    lead_id = fields.Many2one('crm.lead', readonly=True)
    company_id = fields.Many2one('res.company', related='lead_id.company_id', readonly=True)
    opportunity_ids = fields.Many2many('crm.lead', string='Leads/Opportunities')
    merge_destination_opportunity_id = fields.Many2one('crm.lead', string="Destination Opportunity",
                                                       help="The opportunity from the list that will be used as destination. "
                                                            "The information of the destination opportunity will be used in priority when merging",
                                                       context={'merge_opportunity_name_get': True})
    user_id = fields.Many2one('res.users', 'Salesperson', index=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', index=True)

    @api.onchange('opportunity_ids')
    def _onchange_opportunity_ids(self):
        """ When added/removing an opportunity, the merge_destination_opportunity_id should be the one
            which has the highest confidence level
        """
        if self.opportunity_ids:
            opportunity = self._get_highest_opportunity()
            if opportunity:
                self.merge_destination_opportunity_id = opportunity._origin.id
                self.user_id = opportunity.user_id

    @api.onchange('merge_destination_opportunity_id')
    def _onchange_merge_destination_opportunity_id(self):
        """ When modifying the destination opportunity, the user_id should be the one of the destination opportunity.
            If no user is set on the destination opportunity, should be the one which has the highest confidence level
        """
        if self.merge_destination_opportunity_id and self.merge_destination_opportunity_id.user_id:
            self.user_id = self.merge_destination_opportunity_id.user_id
        else:
            highest_opp = self._get_highest_opportunity()
            if highest_opp:
                self.user_id = highest_opp.user_id

    @api.onchange('user_id')
    def _onchange_user_id(self):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of.
        """
        if self.user_id:
            if self.team_id:
                user_in_team = self.env['crm.team'].search_count([('id', '=', self.team_id.id), '|', ('user_id', '=', self.user_id.id), ('member_ids', '=', self.user_id.id)])
            else:
                user_in_team = False
            if not user_in_team:
                values = self.env['crm.lead']._onchange_user_values(self.user_id.id if self.user_id else False)
                self.team_id = values.get('team_id', False)

    def _get_highest_opportunity(self):
        """ Retrieves the opportunity that has the highest confidence level amongst the opportunity_ids. """
        if self.opportunity_ids:
            sorted_opportunities = self.opportunity_ids.filtered(lambda x: x.user_id)._sort_by_confidence_level(reverse=True)
            if sorted_opportunities:
                return sorted_opportunities[0]
            return self.opportunity_ids[0]
        return None
