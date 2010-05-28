##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import tools
import ir
import pooler
import netsvc
from mx import DateTime
import time
from tools.translate import _

class procurement_order(osv.osv):
    _inherit = 'procurement.order'
    def check_buy(self, cr, uid, ids, context=None):
        for procurement in self.browse(cr, uid, ids):
            for line in procurement.product_id.flow_pull_ids:
                print line.location_src_id.name, line.location_id.name, line.type_proc
                if line.location_id==procurement.location_id:
                    return line.type_proc=='buy'
        return super(procurement_order, self).check_buy(cr, uid, ids)

    def check_produce(self, cr, uid, ids, context=None):
        for procurement in self.browse(cr, uid, ids):
            for line in procurement.product_id.flow_pull_ids:
                if line.location_id==procurement.location_id:
                    return line.type_proc=='produce'
        return super(procurement_order, self).check_produce(cr, uid, ids)

    def check_move(self, cr, uid, ids, context=None):
        for procurement in self.browse(cr, uid, ids):
            for line in procurement.product_id.flow_pull_ids:
                if line.location_id==procurement.location_id:
                    if not line.location_src_id:
                        self.write(cr, uid, procurement.id, {'message': _('No source location defined to generate the picking !')})
                    return (line.type_proc=='move') and (line.location_src_id)
        return False

    def action_move_create(self, cr, uid, ids,context=None):
        proc_obj = self.pool.get('procurement.order')
        move_obj = self.pool.get('stock.move')
        location_obj = self.pool.get('stock.location')
        wf_service = netsvc.LocalService("workflow")

        for proc in proc_obj.browse(cr, uid, ids, context=context):
            line = None
            for line in proc.product_id.flow_pull_ids:
                if line.location_id==proc.location_id:
                    break
            assert line, 'Line can not be False if we are on this state of the workflow'
            origin = (proc.origin or proc.name or '').split(':')[0] +':'+line.name
            picking_id = self.pool.get('stock.picking').create(cr, uid, {
                'origin': origin,
                'company_id': line.company_id and line.company_id.id or False,
                'type': line.picking_type,
                'move_type': 'one',
                'address_id': line.partner_address_id.id,
                'note': line.name, # TODO: note on procurement ?
                'invoice_state': 'none',
            })
            move_id = self.pool.get('stock.move').create(cr, uid, {
                'name': line.name,
                'picking_id': picking_id,
                'company_id': line.company_id and line.company_id.id or False,
                'product_id': proc.product_id.id,
                'date_planned': proc.date_planned,
                'product_qty': proc.product_qty,
                'product_uom': proc.product_uom.id,
                'product_uos_qty': (proc.product_uos and proc.product_uos_qty)\
                        or proc.product_qty,
                'product_uos': (proc.product_uos and proc.product_uos.id)\
                        or proc.product_uom.id,
                'address_id': line.partner_address_id.id,
                'location_id': line.location_src_id.id,
                'location_dest_id': line.location_id.id,
                'move_dest_id': proc.move_id and proc.move_id.id or False, # to verif, about history ?
                'tracking_id': False,
                'cancel_cascade': line.cancel_cascade,
                'state': 'confirmed',
                'note': line.name, # TODO: same as above
            })
            if proc.move_id and proc.move_id.state in ('confirmed'):
                self.pool.get('stock.move').write(cr,uid, [proc.move_id.id],  {
                    'state':'waiting'
                }, context=context)
            proc_id = self.pool.get('procurement.order').create(cr, uid, {
                'name': line.name,
                'origin': origin,
                'company_id': line.company_id and line.company_id.id or False,
                'date_planned': proc.date_planned,
                'product_id': proc.product_id.id,
                'product_qty': proc.product_qty,
                'product_uom': proc.product_uom.id,
                'product_uos_qty': (proc.product_uos and proc.product_uos_qty)\
                        or proc.product_qty,
                'product_uos': (proc.product_uos and proc.product_uos.id)\
                        or proc.product_uom.id,
                'location_id': line.location_src_id.id,
                'procure_method': line.procure_method,
                'move_id': move_id,
            })
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
            wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)
            if proc.move_id:
                self.pool.get('stock.move').write(cr, uid, [proc.move_id.id],
                    {'location_id':proc.location_id.id})

            self.write(cr, uid, [proc.id], {'state':'running','message':_('Moved from other location')})

        return False


procurement_order()
