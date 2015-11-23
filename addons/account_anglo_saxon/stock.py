# -*- encoding: utf-8 -*-
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

from openerp.osv import osv

class stock_move(osv.Model):
    _inherit = "stock.move"

    def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):
        """ Add a reference to the stock.move in the invoice line and add the Anglo-Saxon account in the invoice line.
        """
        res = super(stock_move, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=context)
        vals = {'move_id' : move.id}
        if inv_type in ('in_invoice', 'in_refund'):
            fiscal_position = partner.property_account_position
            if move.product_id.type != 'service':
                oa = move.product_id.property_stock_account_input and move.product_id.property_stock_account_input.id
                if not oa:
                    oa = move.product_id.categ_id.property_stock_account_input_categ and move.product_id.categ_id.property_stock_account_input_categ.id        
                if oa:
                    fpos = fiscal_position or False
                    a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, oa)
                    vals.update({'account_id':a})
        res.update(vals)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: