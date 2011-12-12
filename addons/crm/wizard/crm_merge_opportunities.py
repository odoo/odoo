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
from osv import osv, fields
from tools.translate import _

class crm_merge_opportunity(osv.osv_memory):
    """Merge two Opportunities"""

    _name = 'crm.merge.opportunity'
    _description = 'Merge two Opportunities'

    def action_merge(self, cr, uid, ids, context=None):
        lead = self.pool.get('crm.lead')
        record = self.browse(cr, uid, ids[0], context=context)
        opportunities = record.opportunity_ids
        #TOFIX: why need to check lead_ids here
        lead_ids = [opportunities[0].id]
        self.write(cr, uid, ids, {'opportunity_ids' : [(6,0, lead_ids)]}, context=context)
        context['lead_ids'] = lead_ids
        merge_id = lead.merge_opportunity(cr, uid, [x.id for x in opportunities], context=context)
        return lead.redirect_opportunity_view(cr, uid, merge_id, context=context)

    _columns = {
        'opportunity_ids' : fields.many2many('crm.lead',  'merge_opportunity_rel', 'merge_id', 'opportunity_id', 'Opportunities', domain=[('type', '=', 'opportunity')]),
    }

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        """
        record_ids = context and context.get('active_ids', False) or False
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

crm_merge_opportunity()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
