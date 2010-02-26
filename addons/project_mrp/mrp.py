# -*- encoding: utf-8 -*-
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
import tools

class mrp_procurement(osv.osv):
    _name = "mrp.procurement"
    _inherit = "mrp.procurement"
    
    def action_produce_assign_service(self, cr, uid, ids, context={}):
        for procurement in self.browse(cr, uid, ids):
            sline = self.pool.get('sale.order.line')
            content = ''
            sale_order = self.pool.get('sale.order')
            so_ref =  procurement.name.split(':')[0]
            order_ids = sale_order.search(cr, uid, [('name','=',so_ref)], context)

            if order_ids:
                sale_ids = sale_order.read(cr, uid, order_ids[0],['order_line'],context=context)['order_line']
            else:
                so_ref =  procurement.origin.split(':')[0]
                sale_ids = sline.search(cr, uid, [('procurement_id','=',procurement.id)], context)
            l = None
            project_id = None
            analytic_account_id = False
            partner_id = False
            
            for line in sline.browse(cr, uid, sale_ids, context=context):
                content += (line.notes or '')
                l = line
                partner_id = line.order_id.partner_id.id
                if line.order_id.project_id:
                    analytic_account_id = line.order_id.project_id.id
                    partner_id = line.order_id.partner_id.id
                    content+="\n\n"+line.order_id.project_id.complete_name
                    break
            
            # Creating a project for task.Project is created from Procurement.
            proj_name = tools.ustr(so_ref)
            proj_exist_id = self.pool.get('project.project').search(cr, uid, [('name','=',proj_name)], context=context)
            if  not proj_exist_id:
                project_id = self.pool.get('project.project').create(cr, uid, {'name':proj_name,'category_id':analytic_account_id, 'partner_id':partner_id})
            else:
                project_id = proj_exist_id[0]
                
            self.write(cr, uid, [procurement.id], {'state':'running'})
            
            name_task = ('','')
            if procurement.product_id.type == 'service':
                proc_name = procurement.name
                if procurement.origin == proc_name:
                    proc_name = procurement.product_id.name
                    
                name_task = (procurement.origin, proc_name or '')
            else:
                name_task = (procurement.product_id.name or procurement.origin, procurement.name or '')
                
            task_id = self.pool.get('project.task').create(cr, uid, {
                'name': '%s:%s' % name_task,
                'date_deadline': procurement.date_planned,
                'planned_hours': procurement.product_qty,
                'remaining_hours': procurement.product_qty,
                'user_id': procurement.product_id.product_manager.id,
                'notes': "b"+(l and l.order_id.note or ''),
                'procurement_id': procurement.id,
                'description': content,
                'date_deadline': procurement.date_planned,
                'state': 'draft',
                'partner_id': l and l.order_id.partner_id.id or False,
                'project_id': project_id,
            },context=context)
        return task_id
mrp_procurement()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

