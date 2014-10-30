##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, api, fields, _

class crm_merge_opportunity(models.TransientModel):
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
    user_id = fields.Many2one('res.users', 'Salesperson', select=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', select=True)

    @api.multi
    def action_merge(self):
        print"****action_merge****crm_merge_opportunity"
        opportunity2merge_ids = self.opportunity_ids
        print"----opportunity2merge_ids : ",opportunity2merge_ids
        #TODO: why is this passed through the context ?
        self = self.with_context(lead_ids = [opportunity2merge_ids[0].id])
        merge_result = self.opportunity_ids.merge_opportunity(self.user_id.id, self.team_id.id)
        # The newly created lead might be a lead or an opp: redirect toward the right view
        # merge_result = lead_obj.browse(self._cr, self._uid, merge_id, context=self._context)
        print"----merge_result : ",merge_result
        print"****end action_merge****crm_merge_opportunity"
        if merge_result.type == 'opportunity':
            return merge_result.redirect_opportunity_view()
        else:
            return merge_result.redirect_lead_view()

    @api.model
    def default_get(self, fields):
        """
        Use active_ids from the context to fetch the leads/opps to merge.
        In order to get merged, these leads/opps can't be in 'Dead' or 'Closed'
        """
        print"****default_get****mo"
        record_ids = self._context.get('active_ids', False)
        print"----record_ids : ",record_ids
        res = super(crm_merge_opportunity, self).default_get(fields)
        if record_ids:
            opp_ids = []
            opps = self.pool['crm.lead'].browse(self._cr, self._uid, record_ids, context=self._context)
            for opp in opps:
                if opp.probability < 100:
                    opp_ids.append(opp.id)
            if 'opportunity_ids' in fields:
                res.update({'opportunity_ids': opp_ids})
        print"**** end default_get****mo"
        return res

    @api.multi
    def on_change_user(self, user_id, team_id):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of. """
        print"**** on_change_user****crm_merge_opportunity"
        if user_id:
            if team_id:
                user_in_team = self.env['crm.team'].search([('id', '=', team_id), '|', ('user_id', '=', user_id), ('member_ids', '=', user_id)], count=True)
            else:
                user_in_team = False
            if not user_in_team:
                team_id = False
                team_ids = self.env['crm.team'].search(['|', ('user_id', '=', user_id), ('member_ids', '=', user_id)])
                if team_ids:
                    team_id = team_ids[0]
        print"**** end on_change_user****crm_merge_opportunity"
        return {'value': {'team_id': team_id}}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: