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

from osv import fields, osv

class invoice_directly(osv.osv_memory):
    _inherit = 'stock.partial.picking'

    def do_partial(self, cr, uid, ids, context=None):
        """ Makes partial moves and pickings done and 
            launches Create invoice wizard if invoice state is To be Invoiced.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
        result = super(invoice_directly, self).do_partial(cr, uid, ids, context)
        pick_obj = self.pool.get('stock.picking')
        context.update({'active_model':'stock.picking'})
        picking_ids = context.get('active_ids', False)
        if picking_ids:
            context.update({'active_id':picking_ids[0]})
        pick = pick_obj.browse(cr, uid, picking_ids, context=context)[0]
        if pick.invoice_state == '2binvoiced':
            return {
                'name': 'Create Invoice',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.invoice.onshipping',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context
            }
        return {'type': 'ir.actions.act_window_close'}

invoice_directly()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

