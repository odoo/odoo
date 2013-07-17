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
    }

    def action_merge(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        lead_obj = self.pool.get('crm.lead')
        wizard = self.browse(cr, uid, ids[0], context=context)
        opportunity2merge_ids = wizard.opportunity_ids

        #TODO: why is this passed through the context ?
        context['lead_ids'] = [opportunity2merge_ids[0].id]

        merge_id = lead_obj.merge_opportunity(cr, uid, [x.id for x in opportunity2merge_ids], context=context)

        # The newly created lead might be a lead or an opp: redirect toward the right view
        merge_result = lead_obj.browse(cr, uid, merge_id, context=context)

        if merge_result.type == 'opportunity':
            return lead_obj.redirect_opportunity_view(cr, uid, merge_id, context=context)
        else:
            return lead_obj.redirect_lead_view(cr, uid, merge_id, context=context)

    def default_get(self, cr, uid, fields, context=None):
        """
        Use active_ids from the context to fetch the leads/opps to merge.
        In order to get merged, these leads/opps can't be in 'Done' or
        'Cancel' state.
        """
        if context is None:
            context = {}
        record_ids = context.get('active_ids', False)
        res = super(crm_merge_opportunity, self).default_get(cr, uid, fields, context=context)

        if record_ids:
            opp_ids = []
            opps = self.pool.get('crm.lead').browse(cr, uid, record_ids, context=context)
            for opp in opps:
                if opp.state not in ('done', 'cancel'):
                    opp_ids.append(opp.id)
            if 'opportunity_ids' in fields:
                res.update({'opportunity_ids': opp_ids})

        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
