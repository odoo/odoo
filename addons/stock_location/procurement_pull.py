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

from openerp.osv import osv, fields
from openerp.tools.translate import _

class procurement_order(osv.osv):
    _inherit = 'procurement.order'
    
    def check_buy(self, cr, uid, ids, context=None):
        for procurement in self.browse(cr, uid, ids, context=context):
            for line in procurement.product_id.flow_pull_ids:
                if line.location_id==procurement.location_id:
                    return line.type_proc=='buy'
        return super(procurement_order, self).check_buy(cr, uid, ids)

    def check_produce(self, cr, uid, ids, context=None):
        for procurement in self.browse(cr, uid, ids, context=context):
            for line in procurement.product_id.flow_pull_ids:
                if line.location_id==procurement.location_id:
                    return line.type_proc=='produce'
        return super(procurement_order, self).check_produce(cr, uid, ids)

    def check_move(self, cr, uid, ids, context=None):
        for procurement in self.browse(cr, uid, ids, context=context):
            for line in procurement.product_id.flow_pull_ids:
                if line.location_id==procurement.location_id:
                    return (line.type_proc=='move') and (line.location_src_id)
        return False

    def action_move_create(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('stock.move')
        for proc in proc_obj.browse(cr, uid, ids, context=context):
            line = None
            for line in proc.product_id.flow_pull_ids:
                if line.location_id == proc.location_id:
                    break
            assert line, 'Line cannot be False if we are on this state of the workflow'
            origin = (proc.origin or proc.name or '').split(':')[0] +':'+line.name
            move_id = move_obj.create(cr, uid, {
                'name': line.name,
                'company_id':  line.company_id and line.company_id.id or False,
                'product_id': proc.product_id.id,
                'date': proc.date_planned,
                'product_qty': proc.product_qty,
                'product_uom': proc.product_uom.id,
                'product_uos_qty': (proc.product_uos and proc.product_uos_qty)\
                        or proc.product_qty,
                'product_uos': (proc.product_uos and proc.product_uos.id)\
                        or proc.product_uom.id,
                'partner_id': line.partner_address_id.id,
                'location_id': line.location_src_id.id,
                'location_dest_id': line.location_id.id,
                'move_dest_id': proc.move_id and proc.move_id.id or False, # to verif, about history ?
                'tracking_id': False,
                'cancel_cascade': line.cancel_cascade,
                'group_id': proc.group_id.id, 
                'state': 'confirmed',
                'note': _('Move for pulled procurement coming from original location %s, pull rule %s, via original Procurement %s (#%d)') % (proc.location_id.name, line.name, proc.name, proc.id),
            })
            move_obj.button_confirm(cr,uid, [move_id], context=context)
        return False
