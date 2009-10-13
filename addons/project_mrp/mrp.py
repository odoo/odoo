# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv, orm

class mrp_procurement(osv.osv):
    _name = "mrp.procurement"
    _inherit = "mrp.procurement"
    
    def action_produce_assign_service(self, cr, uid, ids, context={}):
        for procurement in self.browse(cr, uid, ids):
            sline = self.pool.get('sale.order.line')
            sale_ids = sline.search(cr, uid, [('procurement_id','=',procurement.id)], context)
            content = ''
            l = None
            project_id = None
            for line in sline.browse(cr, uid, sale_ids, context=context):
                content += (line.notes or '')
                l = line
                if line.order_id.project_id:
                    content+="\n\n"+line.order_id.project_id.complete_name

            self.write(cr, uid, [procurement.id], {'state':'running'})
            task_id = self.pool.get('project.task').create(cr, uid, {
                'name': (procurement.origin or procurement.product_id.name) +': '+(procurement.name or ''),
                'date_deadline': procurement.date_planned,
                'planned_hours': procurement.product_qty,
                'remaining_hours': procurement.product_qty,
                'user_id': procurement.product_id.product_manager.id,
                'notes': "b"+(l and l.order_id.note or ''),
                'procurement_id': procurement.id,
                'description': content,
                'date_deadline': procurement.date_planned,
                'state': 'draft',
                'partner_id': l and l.order_id.partner_id.id or False
            })
        return task_id
mrp_procurement()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

