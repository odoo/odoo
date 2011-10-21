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

from osv import fields,osv

class res_partner(osv.osv):
    """ Inherits partner and adds CRM information in the partner form """
    _inherit = 'res.partner'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'opportunity_ids': fields.one2many('crm.lead', 'partner_id',\
            'Leads and Opportunities'),
        'meeting_ids': fields.one2many('crm.meeting', 'partner_id',\
            'Meetings'),
        'phonecall_ids': fields.one2many('crm.phonecall', 'partner_id',\
            'Phonecalls'),
    }

    def make_opportunity(self, cr, uid, ids, opportunity, planned_revenue=0.0, probability=0.0, partner_id=None. context=None):
        categ = self.pool.get('crm.case.categ')
        address = self.address_get(cr, uid, ids)
        categ_ids = categ.search(cr, uid, [('object_id.model','=','crm.lead')])
        lead = self.pool.get('crm.lead')
        opportunity_ids = []    
        for partner in self.browse(cr, uid, ids, context=context):
            address = self.address_get(cr, uid, partner.id)
            if not partner_id:
                partner_id = partner.id
            opportunity_id = lead.create(cr, uid, {
                'name' : opportunity,
                'planned_revenue' : planned_revenue,
                'probability' : probability,
                'partner_id' : partner_id,
                'partner_address_id' : address['default'],
                'categ_id' : categ_ids and categ_ids[0] or '',
                'state' :'draft',
                'type': 'opportunity'
            })
            opportunity_id.add(opportunity_id)
        return opportunity_ids
res_partner()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
