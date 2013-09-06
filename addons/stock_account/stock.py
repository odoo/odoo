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

#----------------------------------------------------------
# Procurement Rule
#----------------------------------------------------------
class procurement_rule(osv.osv):
    _inherit = 'procurement.rule'
    _columns= {
        'invoice_state': fields.selection([
            ("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not Applicable")], "Invoice Status",
            required=False),
        }
    
#----------------------------------------------------------
# Procurement Order
#----------------------------------------------------------


class procurement_order(osv.osv):
    _inherit = "procurement.order"
    _columns = {
        'invoice_state': fields.selection(
          [("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not Applicable")
          ], "Invoice Control", required=True),
        }

    def _run_move_create(self, cr, uid, procurement, context=None):
        res = super(procurement_order, self)._run_move_create(cr, uid, procurement, context=context)
        res.update({'invoice_state': (procurement.rule_id.invoice_state in ('none', False) and procurement.invoice_state or procurement.rule_id.invoice_state) or 'none'})
        return res
    
    _defaults = {
        'invoice_state': 'none'
        }


#----------------------------------------------------------
# Move
#----------------------------------------------------------

class stock_move(osv.osv):
    _inherit = "stock.move"
    _columns = {
        'invoice_state': fields.selection([("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not Applicable")], "Invoice Control",
            select=True, required=True, track_visibility='onchange', 
            states={'draft': [('readonly', False)]}),
        }
    _defaults= {
        'invoice_state': lambda *args, **argv: 'none'
        }



#----------------------------------------------------------
# Picking
#----------------------------------------------------------

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    def __get_invoice_state(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for pick in self.browse(cr, uid, ids, context=context):
            result[pick.id] = 'none'
            for move in pick.move_lines:
                if move.invoice_state=='invoiced':
                    result[pick.id] = 'invoiced'
                elif move.invoice_state=='2binvoiced':
                    result[pick.id] = '2binvoiced'
                    break
        return result

    def __get_picking_move(self, cr, uid, ids, context={}):
        res = []
        for move in self.pool.get('stock.move').browse(cr, uid, ids, context=context):
            if move.picking_id: 
                res.append(move.picking_id.id)
        return res

    _columns = {
        'invoice_state': fields.function(__get_invoice_state, type='selection', selection=[
            ("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not Applicable")
          ], string="Invoice Control", required=True, 

        store={
          'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['state'], 10),
          'stock.move': (__get_picking_move, ['picking_id', 'invoice_state'], 10),
        },
        ),
    }
    _defaults = {
        'invoice_state': lambda *args, **argv: 'none'
    }

    def action_invoice_create(self, cr, uid, ids, journal_id=False, group=False, type='out_invoice', context=None):
        """ Creates invoice based on the invoice state selected for picking.
        @param journal_id: Id of journal
        @param group: Whether to create a group invoice or not
        @param type: Type invoice to be created
        @return: Ids of created invoices for the pickings
        """
        context = context or {}
        todo = {}
        for picking in self.browse(cr, uid, ids, context=context):
            key = group and picking.id or True
            for move in picking.move_lines:
                if move.procurement_id and (move.procurement_id.invoice_state=='2binvoiced'):
                    if (move.state <> 'cancel') and not move.scrapped:
                        todo.setdefault(key, [])
                        todo[key].append(move)
        invoices = []
        for moves in todo.values():
            invoices = self.__invoice_create_line(cr, uid, moves, journal_id, type, context=context)
        return invoices

    def __invoice_create_line(self, cr, uid, moves, journal_id=False, inv_type='out_invoice', context=None):
        invoice_obj = self.pool.get('account.invoice')
        invoices = {}
        for move in moves:
            sale_line = move.procurement_id.sale_line_id
            sale = sale_line.order_id
            partner = sale.partner_invoice_id

            currency_id = sale.pricelist_id.currency_id.id
            key = (partner.id, currency_id, sale.company_id.id, sale.user_id and sale.user_id.id or False)

            if key not in invoices:
                # Get account and payment terms
                if inv_type in ('out_invoice', 'out_refund'):
                    account_id = partner.property_account_receivable.id
                    payment_term = partner.property_payment_term.id or False
                else:
                    account_id = partner.property_account_payable.id
                    payment_term = partner.property_supplier_payment_term.id or False

                invoice_id = invoice_obj.create(cr, uid, {
                    'origin': sale.name,
                    'date_invoice': context.get('date_inv', False),
                    'user_id': sale.user_id and sale.user_id.id or False,
                    'partner_id': partner.id,
                    'account_id': account_id,
                    'payment_term': payment_term,
                    'type': inv_type,
                    'fiscal_position': partner.property_account_position.id,
                    'company_id': sale.company_id.id,
                    'currency_id': sale.pricelist_id.currency_id.id,
                    'journal_id': journal_id,
                }, context=context)
                invoices[key] = invoice_id

            # Get account_id
            if inv_type in ('out_invoice', 'out_refund'):
                account_id = move.product_id.property_account_income.id
                if not account_id:
                    account_id = move.product_id.categ_id.property_account_income_categ.id
            else:
                account_id = move.product_id.property_account_expense.id
                if not account_id:
                    account_id = move.product_id.categ_id.property_account_expense_categ.id
            fp_obj = self.pool.get('account.fiscal.position')
            fiscal_position = partner.property_account_position
            account_id = fp_obj.map_account(cr, uid, fiscal_position, account_id)

            # set UoS if it's a sale and the picking doesn't have one
            if move.product_uos:
                uos_id = move.product_uos.id
                quantity = move.product_uos_qty
            else:
                uos_id = move.product_uom.id
                quantity = move.product_uom_qty

            invoice_line_id = self.pool.get('account.invoice.line').create(cr, uid, {
                'name': move.name,
                'origin': move.picking_id and move.picking_id.origin or False,
                'invoice_id': invoices[key],
                'account_id': account_id,
                'product_id': move.product_id.id,
                'uos_id': uos_id,
                'quantity': quantity,
                'price_unit': sale_line.price_unit,
                'discount': sale_line.discount,
                'invoice_line_tax_id': [(6, 0, [x.id for x in sale_line.tax_id])],
                'account_analytic_id': sale.project_id and sale.project_id.id or False,
            }, context=context)

            self.pool.get('sale.order.line').write(cr, uid, [sale_line.id], {
                'invoice_lines': [(4, invoice_line_id)]
            }, context=context)
            self.pool.get('sale.order').write(cr, uid, [sale.id], {
                'invoice_ids': [(4, invoices[key])],
            })

            self.pool.get('procurement.order').write(cr, uid, [move.procurement_id.id], {
                'invoice_state': 'invoiced',
            }, context=context)

        invoice_obj.button_compute(cr, uid, invoices.values(), context=context, set_total=(inv_type in ('in_invoice', 'in_refund')))
        return invoices.values()
