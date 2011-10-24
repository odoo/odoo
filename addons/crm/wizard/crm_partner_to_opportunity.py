# -*- coding: utf-8 -*-
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

class crm_partner2opportunity(osv.osv_memory):
    """Converts Partner To Opportunity"""

    _name = 'crm.partner2opportunity'
    _description = 'Partner To Opportunity'

    _columns = {
        'name' : fields.char('Opportunity Name', size=64, required=True),
        'planned_revenue': fields.float('Expected Revenue', digits=(16,2)),
        'probability': fields.float('Success Probability', digits=(16,2)),
        'partner_id': fields.many2one('res.partner', 'Partner'),
    }

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        """
        partner_obj = self.pool.get('res.partner')
        data = context and context.get('active_ids', []) or []
        res = super(crm_partner2opportunity, self).default_get(cr, uid, fields, context=context)

        for partner in partner_obj.browse(cr, uid, data, []):
            if 'name' in fields:
                res.update({'name': partner.name})
            if 'partner_id' in fields:
                res.update({'partner_id': data and data[0] or False})
        return res

    def make_opportunity(self, cr, uid, ids, context=None):
        partner_ids = context and context.get('active_ids', []) or []
        partner = self.pool.get('res.partner')
        lead = self.pool.get('crm.lead')
        data = self.browse(cr, uid, ids, context=context)[0]
        opportunity_ids = partner.make_opportunity(cr, uid, partner_ids,
            data.name,
            data.planned_revenue,
            data.probability,
        )
        opportunity_id = opportunity_ids[partner_ids[0]]
        return lead.redirect_opportunity_view(cr, uid, opportunity_id, context=context)

crm_partner2opportunity()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
