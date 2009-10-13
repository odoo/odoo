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

from osv import osv, fields


class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'property_invoice_type': fields.property(
        'sale_journal.invoice.type',
        type='many2one',
        relation='sale_journal.invoice.type',
        string="Invoicing Method",
        method=True,
        view_load=True,
        group_name="Accounting Properties",
        help="The type of journal used for sales and packing."),
    }
res_partner()

class picking(osv.osv):
    _inherit="stock.picking"
    _columns = {
        'journal_id': fields.many2one('sale_journal.picking.journal', 'Journal'),
        'sale_journal_id': fields.many2one('sale_journal.sale.journal', 'Sale Journal'),
        'invoice_type_id': fields.many2one('sale_journal.invoice.type', 'Invoice Type', readonly=True)
    }
picking()

class sale(osv.osv):
    _inherit="sale.order"
    _columns = {
        'journal_id': fields.many2one('sale_journal.sale.journal', 'Journal'),
        'invoice_type_id': fields.many2one('sale_journal.invoice.type', 'Invoice Type')
    }
    def action_ship_create(self, cr, uid, ids, *args):
        result = super(sale, self).action_ship_create(cr, uid, ids, *args)
        for order in self.browse(cr, uid, ids, context={}):
            pids = [ x.id for x in order.picking_ids]
            self.pool.get('stock.picking').write(cr, uid, pids, {
                'invoice_type_id': order.invoice_type_id.id,
                'sale_journal_id': order.journal_id.id
            })
        return result

    def onchange_partner_id(self, cr, uid, ids, part):
        result = super(sale, self).onchange_partner_id(cr, uid, ids, part)
        if part:
            itype = self.pool.get('res.partner').browse(cr, uid, part).property_invoice_type.id
            result['value']['invoice_type_id'] = itype
        return result
sale()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

