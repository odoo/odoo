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

class invoice_directly(osv.osv_memory):
    _inherit = 'stock.partial.picking'

    def do_partial(self, cr, uid, ids, context=None):
        """Launch Create invoice wizard if invoice state is To be Invoiced,
           after processing the partial picking.
        """
        if context is None: context = {}
        result = super(invoice_directly, self).do_partial(cr, uid, ids, context)
        partial = self.browse(cr, uid, ids[0], context)
        context.update(active_model='stock.picking',
                       active_ids=[partial.picking_id.id])
        if partial.picking_id.invoice_state == '2binvoiced':
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
