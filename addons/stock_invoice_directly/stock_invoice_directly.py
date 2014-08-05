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

from openerp import api
from openerp.osv import osv
from openerp.tools.translate import _


class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    @api.cr_uid_ids_context
    def do_transfer(self, cr, uid, picking_ids, context=None):
        """Launch Create invoice wizard if invoice state is To be Invoiced,
          after processing the picking.
        """
        if context is None:
            context = {}
        res = super(stock_picking, self).do_transfer(cr, uid, picking_ids, context=context)
        pick_ids = [p.id for p in self.browse(cr, uid, picking_ids, context) if p.invoice_state == '2binvoiced']
        if pick_ids:
            context = dict(context, active_model='stock.picking', active_ids=pick_ids)
            return {
                'name': _('Create Invoice'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.invoice.onshipping',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context
            }
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
