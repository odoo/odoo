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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class stock_invoice_onshipping(osv.osv_memory):
    _inherit = "stock.invoice.onshipping"
    
    def _get_journal_type(self, cr, uid, context=None):
        if context is None:
            context = {}
        res_ids = context and context.get('active_ids', [])
        pick_obj = self.pool.get('stock.picking')
        pickings = pick_obj.browse(cr, uid, res_ids, context=context)
        pick = pickings and pickings[0]
        src_usage = pick.move_lines[0].location_id.usage
        dest_usage = pick.move_lines[0].location_dest_id.usage
        pick_purchase = pick.move_lines and pick.move_lines[0].purchase_line_id and pick.move_lines[0].purchase_line_id.order_id.invoice_method == 'picking'
        if pick.picking_type_id.code == 'outgoing' and src_usage == 'supplier' and dest_usage == 'customer' and pick_purchase:
            return 'purchase'
        else:
            return super(stock_invoice_onshipping, self)._get_journal_type(cr, uid, context=context)
        
        
    _defaults = {
        'journal_type': _get_journal_type,
        }