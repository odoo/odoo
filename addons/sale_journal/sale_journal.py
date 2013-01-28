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
        'name': fields.char('Invoice Type', size=64, required=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the invoice type without removing it."),
        'note': fields.text('Note'),
        'invoicing_method': fields.selection([('simple', 'Non grouped'), ('grouped', 'Grouped')], 'Invoicing method', required=True),
    }
    _defaults = {
        'active': True,
        'invoicing_method': 'simple'
    }
sale_journal_invoice_type()

#==============================================
# sale journal inherit
#==============================================

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'property_invoice_type': fields.property(
            'sale_journal.invoice.type',
            type = 'many2one',
            relation = 'sale_journal.invoice.type',
            string = "Invoicing Type",
            view_load = True,
            group_name = "Accounting Properties",
            help = "This invoicing type will be used, by default, to invoice the current partner."),
    }
res_partner()

class picking(osv.osv):
    _inherit = "stock.picking"
    _columns = {
        'invoice_type_id': fields.many2one('sale_journal.invoice.type', 'Invoice Type', readonly=True)
    }
picking()

class stock_picking_in(osv.osv):
    _inherit = "stock.picking.in"
    _columns = {
        'invoice_type_id': fields.many2one('sale_journal.invoice.type', 'Invoice Type', readonly=True)
    }
stock_picking_in()

class stock_picking_out(osv.osv):
    _inherit = "stock.picking.out"
    _columns = {
        'invoice_type_id': fields.many2one('sale_journal.invoice.type', 'Invoice Type', readonly=True)
    }
stock_picking_out()


class sale(osv.osv):
    _inherit = "sale.order"
    _columns = {
        'invoice_type_id': fields.many2one('sale_journal.invoice.type', 'Invoice Type', help="Generate invoice based on the selected option.")
    }

    def _prepare_order_picking(self, cr, uid, order, context=None):
        result = super(sale,self)._prepare_order_picking(cr, uid, order, context=context)
        result.update(invoice_type_id=order.invoice_type_id and order.invoice_type_id.id or False)
        return result

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        result = super(sale, self).onchange_partner_id(cr, uid, ids, part, context=context)
        if part:
            itype = self.pool.get('res.partner').browse(cr, uid, part, context=context).property_invoice_type
            if itype:
                result['value']['invoice_type_id'] = itype.id
        return result

sale()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
