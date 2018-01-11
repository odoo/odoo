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

class sale_journal_invoice_type(osv.osv):
    _name = 'sale_journal.invoice.type'
    _description = 'Invoice Types'
    _columns = {
        'name': fields.char('Invoice Type', required=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the invoice type without removing it."),
        'note': fields.text('Note'),
        'invoicing_method': fields.selection([('simple', 'Non grouped'), ('grouped', 'Grouped')], 'Invoicing method', required=True),
    }
    _defaults = {
        'active': True,
        'invoicing_method': 'simple'
    }

#==============================================
# sale journal inherit
#==============================================

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'property_invoice_type': fields.property(
            type = 'many2one',
            relation = 'sale_journal.invoice.type',
            string = "Invoicing Type",
            group_name = "Accounting Properties",
            help = "This invoicing type will be used, by default, to invoice the current partner."),
    }

    def _commercial_fields(self, cr, uid, context=None):
        return super(res_partner, self)._commercial_fields(cr, uid, context=context) + ['property_invoice_type']


class picking(osv.osv):
    _inherit = "stock.picking"
    _columns = {
        'invoice_type_id': fields.many2one('sale_journal.invoice.type', 'Invoice Type', readonly=True)
    }


class stock_move(osv.osv):
    _inherit = "stock.move"

    def action_confirm(self, cr, uid, ids, context=None):
        """
            Pass the invoice type to the picking from the sales order
            (Should also work in case of Phantom BoMs when on explosion the original move is deleted, similar to carrier_id on delivery)
        """
        procs_to_check = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.procurement_id and move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.invoice_type_id:
                procs_to_check += [move.procurement_id]
        res = super(stock_move, self).action_confirm(cr, uid, ids, context=context)
        pick_obj = self.pool.get("stock.picking")
        for proc in procs_to_check:
            pickings = list(set([x.picking_id.id for x in proc.move_ids if x.picking_id and not x.picking_id.invoice_type_id]))
            if pickings:
                pick_obj.write(cr, uid, pickings, {'invoice_type_id': proc.sale_line_id.order_id.invoice_type_id.id}, context=context)
        return res


class sale(osv.osv):
    _inherit = "sale.order"
    _columns = {
        'invoice_type_id': fields.many2one('sale_journal.invoice.type', 'Invoice Type', help="Generate invoice based on the selected option.")
    }

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        result = super(sale, self).onchange_partner_id(cr, uid, ids, part, context=context)
        if part:
            itype = self.pool.get('res.partner').browse(cr, uid, part, context=context).property_invoice_type
            if itype:
                result['value']['invoice_type_id'] = itype.id
        return result


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
