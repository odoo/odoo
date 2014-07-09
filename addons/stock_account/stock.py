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

class stock_location_path(osv.osv):
    _inherit = "stock.location.path"
    _columns = {
        'invoice_state': fields.selection([
            ("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not Applicable")], "Invoice Status",),
    }
    _defaults = {
        'invoice_state': '',
    }

#----------------------------------------------------------
# Procurement Rule
#----------------------------------------------------------
class procurement_rule(osv.osv):
    _inherit = 'procurement.rule'
    _columns = {
        'invoice_state': fields.selection([
            ("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not Applicable")], "Invoice Status",),
        }
    _defaults = {
        'invoice_state': '',
    }

#----------------------------------------------------------
# Procurement Order
#----------------------------------------------------------


class procurement_order(osv.osv):
    _inherit = "procurement.order"
    _columns = {
        'invoice_state': fields.selection([("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not Applicable")
         ], "Invoice Control"),
        }

    def _run_move_create(self, cr, uid, procurement, context=None):
        res = super(procurement_order, self)._run_move_create(cr, uid, procurement, context=context)
        res.update({'invoice_state': procurement.rule_id.invoice_state or procurement.invoice_state or 'none'})
        return res

    _defaults = {
        'invoice_state': ''
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
    _defaults = {
        'invoice_state': lambda *args, **argv: 'none'
    }

    def _get_master_data(self, cr, uid, move, company, context=None):
        ''' returns a tuple (browse_record(res.partner), ID(res.users), ID(res.currency)'''
        return move.picking_id.partner_id, uid, company.currency_id.id

    def _create_invoice_line_from_vals(self, cr, uid, move, invoice_line_vals, context=None):
        return self.pool.get('account.invoice.line').create(cr, uid, invoice_line_vals, context=context)

    def _get_price_unit_invoice(self, cr, uid, move_line, type, context=None):
        """ Gets price unit for invoice
        @param move_line: Stock move lines
        @param type: Type of invoice
        @return: The price unit for the move line
        """
        if context is None:
            context = {}
        if type in ('in_invoice', 'in_refund'):
            # Take the user company and pricetype
            product = move_line.product_id.with_context(currency_id=move_line.company_id.currency_id.id)
            amount_unit = product.price_get('standard_price')[move_line.product_id.id]
            return amount_unit
        return move_line.product_id.list_price

    def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):
        fp_obj = self.pool.get('account.fiscal.position')
        # Get account_id
        if inv_type in ('out_invoice', 'out_refund'):
            account_id = move.product_id.property_account_income.id
            if not account_id:
                account_id = move.product_id.categ_id.property_account_income_categ.id
        else:
            account_id = move.product_id.property_account_expense.id
            if not account_id:
                account_id = move.product_id.categ_id.property_account_expense_categ.id
        fiscal_position = partner.property_account_position
        account_id = fp_obj.map_account(cr, uid, fiscal_position, account_id)

        # set UoS if it's a sale and the picking doesn't have one
        uos_id = move.product_uom.id
        quantity = move.product_uom_qty
        if move.product_uos:
            uos_id = move.product_uos.id
            quantity = move.product_uos_qty
        return {
            'name': move.name,
            'account_id': account_id,
            'product_id': move.product_id.id,
            'uos_id': uos_id,
            'quantity': quantity,
            'price_unit': self._get_price_unit_invoice(cr, uid, move, inv_type),
            'discount': 0.0,
            'account_analytic_id': False,
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
                if move.invoice_state == 'invoiced':
                    result[pick.id] = 'invoiced'
                elif move.invoice_state == '2binvoiced':
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

    def _create_invoice_from_picking(self, cr, uid, picking, vals, context=None):
        ''' This function simply creates the invoice from the given values. It is overriden in delivery module to add the delivery costs.
        '''
        invoice_obj = self.pool.get('account.invoice')
        return invoice_obj.create(cr, uid, vals, context=context)

    def action_invoice_create(self, cr, uid, ids, journal_id, group=False, type='out_invoice', context=None):
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
                if move.invoice_state == '2binvoiced':
                    if (move.state != 'cancel') and not move.scrapped:
                        todo.setdefault(key, [])
                        todo[key].append(move)
        invoices = []
        for moves in todo.values():
            invoices = self._invoice_create_line(cr, uid, moves, journal_id, type, context=context)
        return invoices

    def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, origin, context=None):
        if context is None:
            context = {}
        partner, currency_id, company_id, user_id = key
        if inv_type in ('out_invoice', 'out_refund'):
            account_id = partner.property_account_receivable.id
            payment_term = partner.property_payment_term.id or False
        else:
            account_id = partner.property_account_payable.id
            payment_term = partner.property_supplier_payment_term.id or False
        return {
            'origin': origin,
            'date_invoice': context.get('date_inv', False),
            'user_id': user_id,
            'partner_id': partner.id,
            'account_id': account_id,
            'payment_term': payment_term,
            'type': inv_type,
            'fiscal_position': partner.property_account_position.id,
            'company_id': company_id,
            'currency_id': currency_id,
            'journal_id': journal_id,
        }

    def _invoice_create_line(self, cr, uid, moves, journal_id, inv_type='out_invoice', context=None):
        invoice_obj = self.pool.get('account.invoice')
        move_obj = self.pool.get('stock.move')
        invoices = {}
        for move in moves:
            company = move.company_id
            origin = move.picking_id.name
            partner, user_id, currency_id = move_obj._get_master_data(cr, uid, move, company, context=context)

            key = (partner, currency_id, company.id, user_id)

            if key not in invoices:
                # Get account and payment terms
                invoice_vals = self._get_invoice_vals(cr, uid, key, inv_type, journal_id, origin, context=context)
                invoice_id = self._create_invoice_from_picking(cr, uid, move.picking_id, invoice_vals, context=context)
                invoices[key] = invoice_id

            invoice_line_vals = move_obj._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=context)
            invoice_line_vals['invoice_id'] = invoices[key]
            invoice_line_vals['origin'] = origin

            move_obj._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
            move_obj.write(cr, uid, move.id, {'invoice_state': 'invoiced'}, context=context)

        invoice_obj.button_compute(cr, uid, invoices.values(), context=context, set_total=(inv_type in ('in_invoice', 'in_refund')))
        return invoices.values()
