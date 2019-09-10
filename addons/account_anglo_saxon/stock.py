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
        """ Add a reference to the stock.move in the invoice line

        In anglo-saxon the price for COGS should be taken from stock.move
        if possible (fallback on standard_price)
        """
        res = super(stock_move, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=context)
        res.update({
            'move_id': move.id,
        })
        return res

class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _description = "Picking List"

    def action_invoice_create(self, cr, uid, ids, journal_id=False,
            group=False, type='out_invoice', context=None):
        '''Return ids of created invoices for the pickings'''
        res = super(stock_picking,self).action_invoice_create(cr, uid, ids, journal_id, group, type, context=context)
        if type in ('in_invoice', 'in_refund'):
            for inv in self.pool.get('account.invoice').browse(cr, uid, res, context=context):
                for ol in inv.invoice_line:
                    if ol.product_id.type != 'service':
                        oa = ol.product_id.property_stock_account_input and ol.product_id.property_stock_account_input.id
                        if not oa:
                            oa = ol.product_id.categ_id.property_stock_account_input_categ and ol.product_id.categ_id.property_stock_account_input_categ.id        
                        if oa:
                            fpos = ol.invoice_id.fiscal_position or False
                            a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, oa)
                            tax_line = ol.invoice_line_tax_id.filtered(lambda l: not l.account_collected_id) if ol.invoice_line_tax_id else False
                            if tax_line:
                                for tax in tax_line:
                                    tax_id = self.pool['account.invoice.tax'].search(cr, uid, [('invoice_id', '=', ol.invoice_id.id), ('name', '=', tax.name), ('account_id', '=', ol.account_id.id)], limit=1)
                                    self.pool['account.invoice.tax'].write(cr, uid, tax_id, {'account_id': a})
                            self.pool.get('account.invoice.line').write(cr, uid, [ol.id], {'account_id': a})
        return res



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
