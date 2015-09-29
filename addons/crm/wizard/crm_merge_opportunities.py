# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import fields, osv
from openerp.tools.translate import _

class crm_merge_opportunity(osv.osv_memory):
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
    _columns = {
        'opportunity_ids': fields.many2many('crm.lead', rel='merge_opportunity_rel', id1='merge_id', id2='opportunity_id', string='Leads/Opportunities'),
        'user_id': fields.many2one('res.users', 'Salesperson', select=True),
        'team_id': fields.many2one('crm.team', 'Sales Team', oldname='section_id', select=True),
    }

    def action_merge(self, cr, uid, ids, context=None):
        context = dict(context or {})

        lead_obj = self.pool.get('crm.lead')
        wizard = self.browse(cr, uid, ids[0], context=context)
        opportunity2merge_ids = wizard.opportunity_ids

        #TODO: why is this passed through the context ?
        context['lead_ids'] = [opportunity2merge_ids[0].id]

        merge_id = lead_obj.merge_opportunity(cr, uid, [x.id for x in opportunity2merge_ids], wizard.user_id.id, wizard.team_id.id, context=context)

        # The newly created lead might be a lead or an opp: redirect toward the right view
        merge_result = lead_obj.browse(cr, uid, merge_id, context=context)

        if merge_result.type == 'opportunity':
            return lead_obj.redirect_opportunity_view(cr, uid, merge_id, context=context)
        else:
            return lead_obj.redirect_lead_view(cr, uid, merge_id, context=context)

    def default_get(self, cr, uid, fields, context=None):
        """
        Use active_ids from the context to fetch the leads/opps to merge.
        In order to get merged, these leads/opps can't be in 'Dead' or 'Closed'
        """
        if context is None:
            context = {}
        record_ids = context.get('active_ids', False)
        res = super(crm_merge_opportunity, self).default_get(cr, uid, fields, context=context)

        if record_ids:
            opp_ids = []
            opps = self.pool.get('crm.lead').browse(cr, uid, record_ids, context=context)
            for opp in opps:
                if opp.probability < 100:
                    opp_ids.append(opp.id)
            if 'opportunity_ids' in fields:
                res.update({'opportunity_ids': opp_ids})

        return res

    def on_change_user(self, cr, uid, ids, user_id, team_id, context=None):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of. """
        if user_id:
            if team_id:
                user_in_team = self.pool.get('crm.team').search(cr, uid, [('id', '=', team_id), '|', ('user_id', '=', user_id), ('member_ids', '=', user_id)], context=context, count=True)
            else:
                user_in_team = False
            if not user_in_team:
                team_id = False
                team_ids = self.pool.get('crm.team').search(cr, uid, ['|', ('user_id', '=', user_id), ('member_ids', '=', user_id)], context=context)
                if team_ids:
                    team_id = team_ids[0]
        return {'value': {'team_id': team_id}}
