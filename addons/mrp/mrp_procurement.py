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

from mx import DateTime
from osv import fields
from osv import osv
from tools.translate import _
import ir
import netsvc
import time

class mrp_procurement(osv.osv):
    _inherit = 'mrp.procurement'
    _columns = {
        'bom_id': fields.many2one('mrp.bom', 'BoM', ondelete='cascade', select=True),
    }
    
    def check_produce_product(self, cr, uid, procurement, context=[]):
        properties = [x.id for x in procurement.property_ids]
        bom_id = self.pool.get('mrp.bom')._bom_find(cr, uid, procurement.product_id.id, procurement.product_uom.id, properties)
        if not bom_id:
            cr.execute('update mrp_procurement set message=%s where id=%s', (_('No BoM defined for this product !'), procurement.id))
            return False
        return True
    
    def action_produce_assign_product(self, cr, uid, ids, context={}):
        """ This is action which call from workflow to assign production order to procurements
        @return: True
        """
        procurement_obj = self.pool.get('mrp.procurement')
        res = procurement_obj.make_mo(cr, uid, ids, context=context)
        res = res.values()
        return len(res) and res[0] or 0 #TO CHECK: why workflow is generated error if return not integer value
    
    def make_mo(self, cr, uid, ids, context={}):
        """ Make Manufacturing(production) order from procurement
        @return: New created Production Orders procurement wise 
        """
        res = {}
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        production_obj = self.pool.get('mrp.production')
        move_obj = self.pool.get('stock.move')
        wf_service = netsvc.LocalService("workflow")
        procurement_obj = self.pool.get('mrp.procurement')
        for procurement in procurement_obj.browse(cr, uid, ids):
            res_id = procurement.move_id.id
            loc_id = procurement.location_id.id
            newdate = DateTime.strptime(procurement.date_planned, '%Y-%m-%d %H:%M:%S') - DateTime.RelativeDateTime(days=procurement.product_id.product_tmpl_id.produce_delay or 0.0)
            newdate = newdate - DateTime.RelativeDateTime(days=company.manufacturing_lead)
            produce_id = production_obj.create(cr, uid, {
                'origin': procurement.origin,
                'product_id': procurement.product_id.id,
                'product_qty': procurement.product_qty,
                'product_uom': procurement.product_uom.id,
                'product_uos_qty': procurement.product_uos and procurement.product_uos_qty or False,
                'product_uos': procurement.product_uos and procurement.product_uos.id or False,
                'location_src_id': procurement.location_id.id,
                'location_dest_id': procurement.location_id.id,
                'bom_id': procurement.bom_id and procurement.bom_id.id or False,
                'date_planned': newdate.strftime('%Y-%m-%d %H:%M:%S'),
                'move_prod_id': res_id,
                'company_id': procurement.company_id.id,
            })
            res[procurement.id] = produce_id
            self.write(cr, uid, [procurement.id], {'state': 'running'})
            bom_result = production_obj.action_compute(cr, uid,
                    [produce_id], properties=[x.id for x in procurement.property_ids])
            wf_service.trg_validate(uid, 'mrp.production', produce_id, 'button_confirm', cr)
            move_obj.write(cr, uid, [res_id],
                    {'location_id': procurement.location_id.id})
        return res
    
mrp_procurement()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
