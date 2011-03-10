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

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

import netsvc
from osv import fields, osv
from tools.translate import _
from decimal import Decimal
import decimal_precision as dp

class pos_config_journal(osv.osv):
    """ Point of Sale journal configuration"""
    _name = 'pos.config.journal'
    _description = "Journal Configuration"

    _columns = {
        'name': fields.char('Description', size=64),
        'code': fields.char('Code', size=64),
        'journal_id': fields.many2one('account.journal', "Journal")
    }

pos_config_journal()


class pos_company_discount(osv.osv):
    """ Company Discount and Cashboxes """
    _inherit = 'res.company'

    _columns = {
        'company_discount': fields.float('Max Discount(%)', digits_compute=dp.get_precision('Point Of Sale')),
        'max_diff': fields.float('Max Difference for Cashboxes', digits_compute=dp.get_precision('Point Of Sale Discount')),
    }

pos_company_discount()

class pos_order(osv.osv):
    """ Point of sale gives business owners a convenient way of checking out customers
        and of recording sales """

    _name = "pos.order"
    _description = "Point of Sale"
    _order = "date_order, create_date desc"

    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            for rec_statement in rec.statement_ids:
                if (rec_statement.statement_id and rec_statement.statement_id.state == 'confirm') or rec.state == 'done':
                    raise osv.except_osv(_('Invalid action !'), _('Cannot delete a point of sale which is closed or contains confirmed cashboxes!'))
        return super(pos_order, self).unlink(cr, uid, ids, context=context)

    def onchange_partner_pricelist(self, cr, uid, ids, part=False, context=None):

        """ Changed price list on_change of partner_id"""
        if not part:
            return {'value': {}}
        pricelist = self.pool.get('res.partner').browse(cr, uid, part, context=context).property_product_pricelist.id
        return {'value': {'pricelist_id': pricelist}}

    def _amount_total(self, cr, uid, ids, field_name, arg, context=None):
        """ Calculates amount_tax of order line
        @param field_names: Names of fields.
        @return: Dictionary of values """
        cr.execute("""
            SELECT
                p.id,
                COALESCE(SUM(
                    l.price_unit*l.qty*(1-(l.discount/100.0)))::decimal(16,2), 0
                    ) AS amount
            FROM pos_order p
            LEFT OUTER JOIN pos_order_line l ON (p.id = l.order_id)
            WHERE p.id IN %s GROUP BY p.id """,(tuple(ids),))
        res = dict(cr.fetchall())
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.partner_id \
               and rec.partner_id.property_account_position \
               and rec.partner_id.property_account_position.tax_ids:
                res[rec.id] = res[rec.id] - rec.amount_tax
            else :
                res[rec.id] = res[rec.id] + rec.amount_tax
        return res

    def _get_date_payment2(self, cr, uid, ids, context=None, *a):
        # Todo need to check this function
        """ Find payment Date
        @param field_names: Names of fields.
        @return: Dictionary of values """
        res = {}
        val = None
        for order in self.browse(cr, uid, ids, context=context):
            cr.execute("SELECT date_payment FROM pos_order WHERE id = %s", (order.id,))
            date_p = cr.fetchone()
            date_p = date_p and date_p[0] or None
            if date_p:
                res[order.id] = date_p
                return res
            cr.execute(" SELECT MAX(l.date) "
                        " FROM account_move_line l, account_move m, account_invoice i, account_move_reconcile r, pos_order o "
                        " WHERE i.move_id = m.id AND l.move_id = m.id AND l.reconcile_id = r.id AND o.id = %s AND o.invoice_id = i.id",
                        (order.id,))
            val = cr.fetchone()
            val = val and val[0] or None
            if val:
                res[order.id] = val
        return res

    def _get_date_payment(self, cr, uid, ids, context, *a):
        """ Find  Validation Date
        @return: Dictionary of values """
        res = {}
        val = None
        for order in self.browse(cr, uid, ids):
            cr.execute("SELECT date_validation FROM pos_order WHERE id = %s", (order.id,))
            date_p = cr.fetchone()
            date_p = date_p and date_p[0] or None
            if date_p:
                res[order.id] = date_p
                return res
            discount_allowed = order.company_id.company_discount
            for line in order.lines:
                if line.discount > discount_allowed:
                    return {order.id: None }
            if order.amount_paid == order.amount_total and not date_p:
                cr.execute("SELECT MAX(date) FROM account_bank_statement_line WHERE pos_statement_id = %s", (order.id,))
                val = cr.fetchone()
                val = val and val[0] or None
            if order.invoice_id and order.invoice_id.move_id and not date_p and not val:
                for o in order.invoice_id.move_id.line_id:
                    if o.balance == 0:
                        if val < o.date_created:
                            val = o.date_created
            if val:
                res[order.id] = val
        return res

    def _amount_all(self, cr, uid, ids, name, args, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_paid': 0.0,
                'amount_return':0.0,
                'amount_tax':0.0,
            }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for payment in order.statement_ids:
                res[order.id]['amount_paid'] +=  payment.amount
                res[order.id]['amount_return'] += (payment.amount < 0 and payment.amount or 0)
            for line in order.lines:
                val1 += line.price_subtotal_incl
                if order.price_type != 'tax_excluded':
                    res[order.id]['amount_tax'] = reduce(lambda x, y: x+round(y['amount'], 2),
                        tax_obj.compute_inv(cr, uid, line.product_id.taxes_id,
                            line.price_unit * \
                            (1-(line.discount or 0.0)/100.0), line.qty),
                            res[order.id]['amount_tax'])
                elif line.qty != 0.0:
                    for c in tax_obj.compute_all(cr, uid, line.product_id.taxes_id, \
                                                 line.price_unit * (1-(line.discount or 0.0)/100.0), \
                                                 line.qty,  line.product_id, line.order_id.partner_id)['taxes']:
                        val += c.get('amount', 0.0)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_total'] = res[order.id]['amount_tax'] + cur_obj.round(cr, uid, cur, val1)
        return res

    def _sale_journal_get(self, cr, uid, context=None):
        """ To get  sale journal for this order
        @return: journal  """
        journal_obj = self.pool.get('account.journal')
        res = journal_obj.search(cr, uid, [('type', '=', 'sale')], limit=1)
        return res and res[0] or False

    def _shop_get(self, cr, uid, context=None):
        """ To get  Shop  for this order
        @return: Shop id  """
        res = self.pool.get('sale.shop').search(cr, uid, [])
        return res and res[0] or False

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'state': 'draft',
            'partner_id': False,
            'invoice_id': False,
            'account_move': False,
            'picking_id': False,
            'statement_ids': [],
            'nb_print': 0,
            'pickings': []
        })
        return super(pos_order, self).copy(cr, uid, id, default, context=context)

    def _get_v( self, cr, uid, ids, *args):
        """ Changed the Validation state of order
        @return: State  """
        res_obj = self.pool.get('res.users')
        company_disc = self.browse(cr, uid, ids)
        list_jrnl = []
        r = {}
        if not company_disc:
            comp = res_obj.browse(cr, uid, uid).company_id.company_discount or 0.0
        else:
            comp = company_disc[0] and company_disc[0].company_id and company_disc[0].company_id.company_discount or 0.0
        cr.execute("SELECT discount FROM pos_order_line WHERE order_id = %s AND discount <= %s", (ids[0], comp))
        res = cr.fetchone()
        cr.execute("SELECT discount FROM pos_order_line WHERE order_id = %s AND discount > %s", (ids[0], comp))
        res2 = cr.fetchone()
        cr.execute("SELECT journal_id FROM account_bank_statement_line WHERE pos_statement_id = %s ", (ids[0], ))
        res3 = cr.fetchall()
        for r in res3:
            cr.execute("SELECT id FROM account_journal WHERE name = '%s' AND special_journal = 't'", (r[0], ))
            res3 = cr.fetchone()
            is_special = res3 and res3[0] or None
            if is_special:
                list_jrnl.append(is_special)
        for order in self.browse(cr, uid, ids):
            if order.state in ('paid', 'done', 'invoiced') and res and not res2 and not len(list_jrnl):
                r[order.id] = 'accepted'
        return r

    _columns = {
        'name': fields.char('Order Description', size=64, required=True,
            states={'draft': [('readonly', False)]}, readonly=True),
        'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
        'num_sale': fields.char('Internal Note', size=64),
        'shop_id': fields.many2one('sale.shop', 'Shop', required=True,
            states={'draft': [('readonly', False)]}, readonly=True),
        'date_order': fields.datetime('Date Ordered', readonly=True, select=True),
        'date_validation': fields.function(_get_date_payment,
                                           method=True,
                                           string='Validation Date',
                                           type='date', select=True, store=True),
        'date_payment': fields.function(_get_date_payment2, method=True,
                                        string='Payment Date',
                                        type='date', select=True, store=True),
        'date_validity': fields.date('Validity Date', required=True),
        'user_id': fields.many2one('res.users', 'Connected Salesman', help="Person who uses the the cash register. It could be a reliever, a student or an interim employee."),
        'user_salesman_id': fields.many2one('res.users', 'Cashier', required=True, help="User who is logged into the system."),
        'sale_manager': fields.many2one('res.users', 'Salesman Manager'),
        'amount_tax': fields.function(_amount_all, method=True, string='Taxes', digits_compute=dp.get_precision('Point Of Sale'), multi='all'),
        'amount_total': fields.function(_amount_all, method=True, string='Total', multi='all'),
        'amount_paid': fields.function(_amount_all, string='Paid', states={'draft': [('readonly', False)]}, readonly=True, method=True, digits_compute=dp.get_precision('Point Of Sale'), multi='all'),
        'amount_return': fields.function(_amount_all, 'Returned', method=True, digits_compute=dp.get_precision('Point Of Sale'), multi='all'),
        'lines': fields.one2many('pos.order.line', 'order_id', 'Order Lines', states={'draft': [('readonly', False)]}, readonly=True),
        'price_type': fields.selection([
                                ('tax_excluded','Tax excluded')],
                                 'Price method', required=True),
        'statement_ids': fields.one2many('account.bank.statement.line', 'pos_statement_id', 'Payments', states={'draft': [('readonly', False)]}, readonly=True),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', required=True, states={'draft': [('readonly', False)]}, readonly=True),
        'partner_id': fields.many2one('res.partner', 'Customer', change_default=True, select=1, states={'draft': [('readonly', False)], 'paid': [('readonly', False)]}),
        'state': fields.selection([('draft', 'Quotation'),
                                   ('payment', 'Payment'),
                                   ('advance','Advance'),
                                   ('paid', 'Paid'),
                                   ('done', 'Done'),
                                   ('invoiced', 'Invoiced'),
                                   ('cancel', 'Cancel')],
                                  'State', readonly=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice'),
        'account_move': fields.many2one('account.move', 'Account Entry', readonly=True),
        'pickings': fields.one2many('stock.picking', 'pos_order', 'Picking', readonly=True),
        'picking_id': fields.many2one('stock.picking', 'Last Output Picking', readonly=True),
        'first_name': fields.char('First Name', size=64),
        'note': fields.text('Internal Notes'),
        'nb_print': fields.integer('Number of Print', readonly=True),
        'sale_journal': fields.many2one('account.journal', 'Journal', required=True, states={'draft': [('readonly', False)]}, readonly=True),
        'invoice_wanted': fields.boolean('Create Invoice'),
        'note_2': fields.char('Customer Note', size=64),
        'type_rec': fields.char('Type of Receipt', size=64),
        'remboursed': fields.boolean('Remboursed'),
        'contract_number': fields.char('Contract Number', size=512, select=1),
        'journal_entry': fields.boolean('Journal Entry'),
    }

    def _select_pricelist(self, cr, uid, context=None):
        """ To get default pricelist for the order
        @param name: Names of fields.
        @return: pricelist ID
        """
        res = self.pool.get('sale.shop').search(cr, uid, [], context=context)
        if res:
            shop = self.pool.get('sale.shop').browse(cr, uid, res[0], context=context)
            return shop.pricelist_id and shop.pricelist_id.id or False
        return False

    def _journal_default(self, cr, uid, context=None):
        """ To get default pricelist for the order
        @param name: Names of fields.
        @return: journal ID
        """
        journal_list = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'cash')])
        return journal_list and journal_list[0] or False

    _defaults = {
        'user_salesman_id':lambda self, cr, uid, context: uid,
        'user_id': lambda self, cr, uid, context: uid,
        'sale_manager': lambda self, cr, uid, context: uid,
        'state': 'draft',
        'price_type': 'tax_excluded',
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'pos.order'),
        'date_order': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'date_validity': lambda *a: (datetime.today() + relativedelta(months=+6)).strftime('%Y-%m-%d'),
        'nb_print': 0,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        'sale_journal': _sale_journal_get,
        'invoice_wanted': False,
        'shop_id': _shop_get,
        'pricelist_id': _select_pricelist,
    }


    def test_order_lines(self, cr, uid, order, context=None):
        """ Test order line is created or not for the order
        @param name: Names of fields.
        @return: True
        """
        if not order.lines:
            raise osv.except_osv(_('Error'), _('No order lines defined for this sale.'))

        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'pos.order', order.id, 'paid', cr)
        return True

    def dummy_button(self, cr, uid, order, context=None):
        return True

    def test_paid(self, cr, uid, ids, context=None):
        """ Test all amount is paid for this order
        @return: True
        """
        for order in self.browse(cr, uid, ids, context=context):
            if order.lines and not order.amount_total:
                return True
            if (not order.lines) or (not order.statement_ids) or \
                Decimal(str(order.amount_total)) != Decimal(str(order.amount_paid)):
                return False
        return True

    def _get_qty_differences(self, orders, old_picking):
        """check if the customer changed the product quantity """
        order_dict = {}
        for order in orders:
            for line in order.lines:
                order_dict[line.product_id.id] = line

        # check the quantity differences:
        diff_dict = {}
        for line in old_picking.move_lines:
            order_line = order_dict.get(line.product_id.id)
            if not order_line:
                deleted = True
                qty_to_delete_from_original_picking = line.product_qty
                diff_dict[line.product_id.id] = (deleted, qty_to_delete_from_original_picking)
            elif line.product_qty != order_line.qty:
                deleted = False
                qty_to_delete_from_original_picking = line.product_qty - order_line.qty
                diff_dict[line.product_id.id] = (deleted, qty_to_delete_from_original_picking)

        return diff_dict

    def _split_picking(self, cr, uid, ids, context, old_picking, diff_dict):
        """if the customer changes the product quantity, split the picking in two"""
        # create a copy of the original picking and adjust the product qty:
        picking_model = self.pool.get('stock.picking')
        defaults = {
            'note': "Partial picking from customer", # add a note to tell why we create a new picking
            'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out'), # increment the sequence
        }

        new_picking_id = picking_model.copy(cr, uid, old_picking.id, defaults) # state = 'draft'
        new_picking = picking_model.browse(cr, uid, new_picking_id, context=context)

        for line in new_picking.move_lines:
            p_id = line.product_id.id
            if p_id in diff_dict:
                diff = diff_dict[p_id]
                deleted = diff[0]
                qty_to_del = diff[1]
                if deleted: # product has been deleted (customer didn't took it):
                    # delete this product from old picking:
                    for old_line in old_picking.move_lines:
                        if old_line.product_id.id == p_id:
                            old_line.write({'state': 'draft'}, context=context) # cannot delete if not draft
                            old_line.unlink(context=context)
                elif qty_to_del > 0: # product qty has been modified (customer took less than the ordered quantity):
                    # subtract qty from old picking:
                    for old_line in old_picking.move_lines:
                        if old_line.product_id.id == p_id:
                            old_line.write({'product_qty': old_line.product_qty - qty_to_del}, context=context)
                    # add qty to new picking:
                    line.write({'product_qty': qty_to_del}, context=context)
                else: # product hasn't changed (customer took it without any change):
                    # delete this product from new picking:
                    line.unlink(context=context)
            else:
                # delete it in the new picking:
                line.unlink(context=context)

    def create_picking(self, cr, uid, ids, context=None):
        """Create a picking for each order and validate it."""
        picking_obj = self.pool.get('stock.picking')
        property_obj = self.pool.get("ir.property")
        move_obj = self.pool.get('stock.move')
        pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
        orders = self.browse(cr, uid, ids, context=context)
        for order in orders:
            if not order.picking_id:
                new = True
                picking_id = picking_obj.create(cr, uid, {
                    'name': pick_name,
                    'origin': order.name,
                    'type': 'out',
                    'state': 'draft',
                    'move_type': 'direct',
                    'note': 'POS notes ' + (order.note or ""),
                    'invoice_state': 'none',
                    'auto_picking': True,
                    'pos_order': order.id,
                }, context=context)
                self.write(cr, uid, [order.id], {'picking_id': picking_id}, context=context)
            else:
                picking_id = order.picking_id.id
                picking_obj.write(cr, uid, [picking_id], {'auto_picking': True}, context=context)
                picking = picking_obj.browse(cr, uid, [picking_id], context=context)[0]
                new = False

                # split the picking (if product quantity has changed):
                diff_dict = self._get_qty_differences(orders, picking)
                if diff_dict:
                    self._split_picking(cr, uid, ids, context, picking, diff_dict)

            if new:
                for line in order.lines:
                    if line.product_id and line.product_id.type == 'service':
                        continue
                    prop_ids = property_obj.search(cr, uid, [('name', '=', 'property_stock_customer')], context=context)
                    val = property_obj.browse(cr, uid, prop_ids[0], context=context).value_reference
                    cr.execute("SELECT s.id FROM stock_location s, stock_warehouse w WHERE w.lot_stock_id = s.id AND w.id = %s", (order.shop_id.warehouse_id.id, ))
                    res = cr.fetchone()
                    location_id = res and res[0] or None
                    stock_dest_id = val.id
                    if line.qty < 0:
                        location_id, stock_dest_id = stock_dest_id, location_id
                    move_obj.create(cr, uid, {
                            'name': '(POS %d)' % (order.id, ),
                            'product_uom': line.product_id.uom_id.id,
                            'product_uos': line.product_id.uom_id.id,
                            'picking_id': picking_id,
                            'product_id': line.product_id.id,
                            'product_uos_qty': abs(line.qty),
                            'product_qty': abs(line.qty),
                            'tracking_id': False,
                            'pos_line_id': line.id,
                            'state': 'waiting',
                            'location_id': location_id,
                            'location_dest_id': stock_dest_id,
                            'prodlot_id': line.prodlot_id and line.prodlot_id.id or False
                        }, context=context)

            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
            picking_obj.force_assign(cr, uid, [picking_id], context)
        return True

    def set_to_draft(self, cr, uid, ids, *args):
        """ Changes order state to draft
        @return: True
        """
        if not len(ids):
            return False
        self.write(cr, uid, ids, {'state': 'draft'})
        wf_service = netsvc.LocalService("workflow")
        for i in ids:
            wf_service.trg_create(uid, 'pos.order', i, cr)
        return True

    def button_invalidate(self, cr, uid, ids, *args):
        """ Check the access for the sale order
        @return: True
        """
        res_obj = self.pool.get('res.company')
        try:
            part_company = res_obj.browse(cr, uid, uid) and res_obj.browse(cr, uid, uid).parent_id and res_obj.browse(cr, uid, uid).parent_id.id or None
        except Exception:
            raise osv.except_osv(_('Error'), _('You don\'t have enough access to validate this sale!'))
        if part_company:
            raise osv.except_osv(_('Error'), _('You don\'t have enough access to validate this sale!'))
        return True

    def cancel_order(self, cr, uid, ids, context=None):
        """ Changes order state to cancel
        @return: True
        """
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        self.cancel_picking(cr, uid, ids, context=context)
        return True

    def add_payment(self, cr, uid, order_id, data, context=None):
        """Create a new payment for the order"""
        statement_obj = self.pool.get('account.bank.statement')
        statement_line_obj = self.pool.get('account.bank.statement.line')
        prod_obj = self.pool.get('product.product')
        property_obj = self.pool.get('ir.property')
        curr_c = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        curr_company = curr_c.id
        order = self.browse(cr, uid, order_id, context=context)
        if not order.num_sale and data['num_sale']:
            self.write(cr, uid, order_id, {'num_sale': data['num_sale']}, context=context)
        ids_new = []
        args = {
            'amount': data['amount'],
        }
        if 'payment_date' in data.keys():
            args['date'] = data['payment_date']
        if 'payment_name' in data.keys():
            args['name'] = data['payment_name'] + ' ' + order.name
        account_def = property_obj.get(cr, uid, 'property_account_receivable', 'res.partner', context=context)
        args['account_id'] = order.partner_id and order.partner_id.property_account_receivable \
                             and order.partner_id.property_account_receivable.id or account_def.id or curr_c.account_receivable.id
        if data.get('is_acc', False):
            args['is_acc'] = data['is_acc']
            args['account_id'] = prod_obj.browse(cr, uid, data['product_id'], context=context).property_account_income \
                                 and prod_obj.browse(cr, uid, data['product_id'], context=context).property_account_income.id
            if not args['account_id']:
                raise osv.except_osv(_('Error'), _('Please provide an account for the product: %s')% \
                                     (prod_obj.browse(cr, uid, data['product_id'], context=context).name))
        args['partner_id'] = order.partner_id and order.partner_id.id or None
        args['ref'] = order.contract_number or None

        statement_id = statement_obj.search(cr,uid, [
                                                     ('journal_id', '=', data['journal']),
                                                     ('company_id', '=', curr_company),
                                                     ('user_id', '=', uid),
                                                     ('state', '=', 'open')], context=context)
        if len(statement_id) == 0:
            raise osv.except_osv(_('Error !'), _('You have to open at least one cashbox'))
        if statement_id:
            statement_id = statement_id[0]
        args['statement_id'] = statement_id
        args['pos_statement_id'] = order_id
        args['journal_id'] = data['journal']
        args['type'] = 'customer'
        args['ref'] = order.name
        statement_line_obj.create(cr, uid, args, context=context)
        ids_new.append(statement_id)

        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'pos.order', order_id, 'paid', cr)
        wf_service.trg_write(uid, 'pos.order', order_id, cr)

        return statement_id

    def add_product(self, cr, uid, order_id, product_id, qty, context=None):

        """Create a new order line the order"""

        line_obj = self.pool.get('pos.order.line')
        values = self.read(cr, uid, order_id, ['partner_id', 'pricelist_id'])

        pricelist = values['pricelist_id'] and values['pricelist_id'][0]
        product = values['partner_id'] and values['partner_id'][0]

        price = line_obj.price_by_product(cr, uid, [],
                pricelist, product_id, qty, product)

        order_line_id = line_obj.create(cr, uid, {
            'order_id': order_id,
            'product_id': product_id,
            'qty': qty,
            'price_unit': price,
        }, context=context)
        return order_line_id, price

    def refund(self, cr, uid, ids, context=None):

        """Create a copy of order  for refund order"""

        clone_list = []
        line_obj = self.pool.get('pos.order.line')

        for order in self.browse(cr, uid, ids, context=context):
            clone_id = self.copy(cr, uid, order.id, {
                'name': order.name + ' REFUND',
                'date_order': time.strftime('%Y-%m-%d'),
                'state': 'draft',
                'note': 'REFUND\n'+ (order.note or ''),
                'invoice_id': False,
                'nb_print': 0,
                'statement_ids': False,
                }, context=context)
            clone_list.append(clone_id)


        for clone in self.browse(cr, uid, clone_list, context=context):
            for order_line in clone.lines:
                line_obj.write(cr, uid, [order_line.id], {
                    'qty': -order_line.qty
                    }, context=context)
        return clone_list

    def action_invoice(self, cr, uid, ids, context=None):

        """Create a invoice of order  """

        inv_ref = self.pool.get('account.invoice')
        inv_line_ref = self.pool.get('account.invoice.line')
        product_obj = self.pool.get('product.product')
        inv_ids = []

        for order in self.pool.get('pos.order').browse(cr, uid, ids, context=context):
            if order.invoice_id:
                inv_ids.append(order.invoice_id.id)
                continue

            if not order.partner_id:
                raise osv.except_osv(_('Error'), _('Please provide a partner for the sale.'))

            acc = order.partner_id.property_account_receivable.id
            inv = {
                'name': 'Invoice from POS: '+order.name,
                'origin': order.name,
                'account_id': acc,
                'journal_id': order.sale_journal.id or None,
                'type': 'out_invoice',
                'reference': order.name,
                'partner_id': order.partner_id.id,
                'comment': order.note or '',
                'currency_id': order.pricelist_id.currency_id.id, # considering partner's sale pricelist's currency
            }
            inv.update(inv_ref.onchange_partner_id(cr, uid, [], 'out_invoice', order.partner_id.id)['value'])
            if not inv.get('account_id', None):
                inv['account_id'] = acc
            inv_id = inv_ref.create(cr, uid, inv, context=context)

            self.write(cr, uid, [order.id], {'invoice_id': inv_id, 'state': 'invoiced'}, context=context)
            inv_ids.append(inv_id)
            for line in order.lines:
                inv_line = {
                    'invoice_id': inv_id,
                    'product_id': line.product_id.id,
                    'quantity': line.qty,
                }
                inv_name = product_obj.name_get(cr, uid, [line.product_id.id], context=context)[0][1]

                inv_line.update(inv_line_ref.product_id_change(cr, uid, [],
                                                               line.product_id.id,
                                                               line.product_id.uom_id.id,
                                                               line.qty, partner_id = order.partner_id.id,
                                                               fposition_id=order.partner_id.property_account_position.id)['value'])
                inv_line['price_unit'] = line.price_unit
                inv_line['discount'] = line.discount
                inv_line['name'] = inv_name
                inv_line['invoice_line_tax_id'] = ('invoice_line_tax_id' in inv_line)\
                    and [(6, 0, inv_line['invoice_line_tax_id'])] or []
                inv_line_ref.create(cr, uid, inv_line, context=context)

        for i in inv_ids:
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'account.invoice', i, 'invoice_open', cr)
        return inv_ids

    def create_account_move(self, cr, uid, ids, context=None):
        """Create a account move line of order  """
        account_move_obj = self.pool.get('account.move')
        account_move_line_obj = self.pool.get('account.move.line')
        account_period_obj = self.pool.get('account.period')
        account_tax_obj = self.pool.get('account.tax')
        res_obj=self.pool.get('res.users')
        property_obj=self.pool.get('ir.property')
        period = account_period_obj.find(cr, uid, context=context)[0]

        for order in self.browse(cr, uid, ids, context=context):
            curr_c = res_obj.browse(cr, uid, uid).company_id
            comp_id = res_obj.browse(cr, order.user_id.id, order.user_id.id).company_id
            comp_id = comp_id and comp_id.id or False
            to_reconcile = []
            group_tax = {}
            account_def = property_obj.get(cr, uid, 'property_account_receivable', 'res.partner', context=context).id

            order_account = order.partner_id and order.partner_id.property_account_receivable and order.partner_id.property_account_receivable.id or account_def or curr_c.account_receivable.id

            # Create an entry for the sale
            move_id = account_move_obj.create(cr, uid, {
                'journal_id': order.sale_journal.id,
                'period_id': period,
                }, context=context)

            # Create an move for each order line
            for line in order.lines:
                tax_amount = 0
                taxes = [t for t in line.product_id.taxes_id]
                if order.price_type == 'tax_excluded':
                    computed_taxes = account_tax_obj.compute_all(
                        cr, uid, taxes, line.price_unit, line.qty)['taxes']
                else:
                    computed_taxes = account_tax_obj.compute_inv(
                        cr, uid, taxes, line.price_unit, line.qty)

                for tax in computed_taxes:
                    tax_amount += round(tax['amount'], 2)
                    group_key = (tax['tax_code_id'],
                                tax['base_code_id'],
                                tax['account_collected_id'])

                    if group_key in group_tax:
                        group_tax[group_key] += round(tax['amount'], 2)
                    else:
                        group_tax[group_key] = round(tax['amount'], 2)
                if order.price_type != 'tax_excluded':
                    amount = line.price_subtotal - tax_amount
                else:
                    amount = line.price_subtotal

                # Search for the income account
                if  line.product_id.property_account_income.id:
                    income_account = line.\
                                    product_id.property_account_income.id
                elif line.product_id.categ_id.\
                        property_account_income_categ.id:
                    income_account = line.product_id.categ_id.\
                                    property_account_income_categ.id
                else:
                    raise osv.except_osv(_('Error !'), _('There is no income '\
                        'account defined for this product: "%s" (id:%d)') \
                        % (line.product_id.name, line.product_id.id, ))

                # Empty the tax list as long as there is no tax code:
                tax_code_id = False
                tax_amount = 0
                while computed_taxes:
                    tax = computed_taxes.pop(0)
                    if amount > 0:
                        tax_code_id = tax['base_code_id']
                        tax_amount = line.price_subtotal * tax['base_sign']
                    else:
                        tax_code_id = tax['ref_base_code_id']
                        tax_amount = line.price_subtotal * tax['ref_base_sign']
                    # If there is one we stop
                    if tax_code_id:
                        break

                # Create a move for the line
                account_move_line_obj.create(cr, uid, {
                    'name': "aa"+order.name,
                    'date': order.date_order[:10],
                    'ref': order.contract_number or order.name,
                    'quantity': line.qty,
                    'product_id': line.product_id.id,
                    'move_id': move_id,
                    'account_id': income_account,
                    'company_id': comp_id,
                    'credit': ((amount>0) and amount) or 0.0,
                    'debit': ((amount<0) and -amount) or 0.0,
                    'journal_id': order.sale_journal.id,
                    'period_id': period,
                    'tax_code_id': tax_code_id,
                    'tax_amount': tax_amount,
                    'partner_id': order.partner_id and order.partner_id.id or False
                }, context=context)

                # For each remaining tax with a code, whe create a move line
                for tax in computed_taxes:
                    if amount > 0:
                        tax_code_id = tax['base_code_id']
                        tax_amount = line.price_subtotal * tax['base_sign']
                    else:
                        tax_code_id = tax['ref_base_code_id']
                        tax_amount = line.price_subtotal * tax['ref_base_sign']
                    if not tax_code_id:
                        continue

                    account_move_line_obj.create(cr, uid, {
                        'name': "bb" + order.name,
                        'date': order.date_order[:10],
                        'ref': order.contract_number or order.name,
                        'product_id':line.product_id.id,
                        'quantity': line.qty,
                        'move_id': move_id,
                        'account_id': income_account,
                        'company_id': comp_id,
                        'credit': 0.0,
                        'debit': 0.0,
                        'journal_id': order.sale_journal.id,
                        'period_id': period,
                        'tax_code_id': tax_code_id,
                        'tax_amount': tax_amount,
                    }, context=context)


            # Create a move for each tax group
            (tax_code_pos, base_code_pos, account_pos)= (0, 1, 2)
            for key, amount in group_tax.items():
                account_move_line_obj.create(cr, uid, {
                    'name': "cc" + order.name,
                    'date': order.date_order[:10],
                    'ref': order.contract_number or order.name,
                    'move_id': move_id,
                    'company_id': comp_id,
                    'quantity': line.qty,
                    'product_id': line.product_id.id,
                    'account_id': key[account_pos],
                    'credit': ((amount>0) and amount) or 0.0,
                    'debit': ((amount<0) and -amount) or 0.0,
                    'journal_id': order.sale_journal.id,
                    'period_id': period,
                    'tax_code_id': key[tax_code_pos],
                    'tax_amount': amount,
                }, context=context)

            # counterpart
            to_reconcile.append(account_move_line_obj.create(cr, uid, {
                'name': "dd" + order.name,
                'date': order.date_order[:10],
                'ref': order.contract_number or order.name,
                'move_id': move_id,
                'company_id': comp_id,
                'account_id': order_account,
                'credit': ((order.amount_total < 0) and -order.amount_total)\
                    or 0.0,
                'debit': ((order.amount_total > 0) and order.amount_total)\
                    or 0.0,
                'journal_id': order.sale_journal.id,
                'period_id': period,
                'partner_id': order.partner_id and order.partner_id.id or False
            }, context=context))


            # search the account receivable for the payments:
            account_receivable = order.sale_journal.default_credit_account_id.id
            if not account_receivable:
                raise  osv.except_osv(_('Error !'),
                    _('There is no receivable account defined for this journal:'\
                    ' "%s" (id:%d)') % (order.sale_journal.name, order.sale_journal.id, ))
            for payment in order.statement_ids:
                # Create one entry for the payment
                if payment.is_acc:
                    continue
                account_move_obj.create(cr, uid, {
                    'journal_id': payment.statement_id.journal_id.id,
                    'period_id': period,
                }, context=context)

            for stat_l in order.statement_ids:
                if stat_l.is_acc and len(stat_l.move_ids):
                    for st in stat_l.move_ids:
                        for s in st.line_id:
                            if s.credit:
                                account_move_line_obj.copy(cr, uid, s.id, {
                                                        'debit': s.credit,
                                                        'statement_id': False,
                                                        'credit': s.debit
                                                    })
                                account_move_line_obj.copy(cr, uid, s.id, {
                                                        'statement_id': False,
                                                        'account_id': order_account
                                                     })

            self.write(cr, uid, order.id, {'state':'done'}, context=context)
        return True

    def cancel_picking(self, cr, uid, ids, context=None):
        stock_picking_obj = self.pool.get('stock.picking')
        for order in self.browse(cr, uid, ids, context=context):
            for picking in order.pickings:
                stock_picking_obj.unlink(cr, uid, [picking.id], context=context)
        return True


    def action_payment(self, cr, uid, ids, context=None):
        vals = {'state': 'payment'}
        sequence_obj = self.pool.get('ir.sequence')
        for pos in self.browse(cr, uid, ids, context=context):
            create_contract_nb = False
            for line in pos.lines:
                if line.product_id.product_type == 'MD':
                    create_contract_nb = True
                    break
            if create_contract_nb:
                seq = sequence_obj.get(cr, uid, 'pos.user_%s' % pos.user_salesman_id.login)
                vals['contract_number'] = '%s-%s' % (pos.user_salesman_id.login, seq)
        self.write(cr, uid, ids, vals, context=context)

    def action_paid(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if context.get('flag', False):
            self.create_picking(cr, uid, ids, context=None)
            self.write(cr, uid, ids, {'state': 'paid'}, context=context)
        else:
            context['flag'] = True
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True

    def action_done(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            if not order.journal_entry:
                self.create_account_move(cr, uid, ids, context=None)
        return True

    def compute_state(self, cr, uid, id):
        cr.execute("SELECT act.id, act.name FROM wkf_activity act "
                   "INNER JOIN wkf_workitem item ON act.id = item.act_id "
                   "INNER JOIN wkf_instance inst ON item.inst_id = inst.id "
                   "INNER JOIN wkf ON inst.wkf_id = wkf.id "
                   "WHERE wkf.osv = 'pos.order' AND inst.res_id = %s "
                   "ORDER BY act.name", (id, ))
        return [name for id, name in cr.fetchall()]

pos_order()

class account_bank_statement(osv.osv):
    _inherit = 'account.bank.statement'
    _columns= {
        'user_id': fields.many2one('res.users', ondelete='cascade', string='User', readonly=True),
    }
    _defaults = {
        'user_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).id
    }
account_bank_statement()

class account_bank_statement_line(osv.osv):
    _inherit = 'account.bank.statement.line'
    def _get_statement_journal(self, cr, uid, ids, context, *a):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id] = line.statement_id and line.statement_id.journal_id and line.statement_id.journal_id.name or None
        return res
    _columns= {
        'journal_id': fields.function(_get_statement_journal, method=True,store=True, string='Journal', type='char', size=64),
        'am_out': fields.boolean("To count"),
        'is_acc': fields.boolean("Is accompte"),
        'pos_statement_id': fields.many2one('pos.order', ondelete='cascade'),
    }
account_bank_statement_line()

class pos_order_line(osv.osv):
    _name = "pos.order.line"
    _description = "Lines of Point of Sale"

    def _get_amount(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = self.price_by_product(cr, uid, ids, line.order_id.pricelist_id.id, line.product_id.id, line.qty, line.order_id.partner_id.id)
            res[line.id] = price
        return res

    def _amount_line_ttc(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, 0.0)
        account_tax_obj = self.pool.get('account.tax')
        self.price_by_product_multi(cr, uid, ids)
        for line in self.browse(cr, uid, ids, context=context):
            tax_amount = 0.0
            taxes = [t for t in line.product_id.taxes_id]
            if line.qty == 0.0:
                continue
            computed_taxes = account_tax_obj.compute_all(cr, uid, taxes, line.price_unit, line.qty)['taxes']
            for tax in computed_taxes:
                tax_amount += tax['amount']
            if line.discount != 0.0:
                res[line.id] = line.price_unit * line.qty * (1 - (line.discount or 0.0) / 100.0)
            else:
                res[line.id] = line.price_unit*line.qty
            res[line.id] = res[line.id] + tax_amount
        return res

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        self.price_by_product_multi(cr, uid, ids)
        for line in self.browse(cr, uid, ids, context=context):
            if line.discount!=0.0:
                res[line.id] = line.price_unit * line.qty * (1 - (line.discount or 0.0) / 100.0)
            else:
                res[line.id] = line.price_unit * line.qty
        return res

    def _amount_line_all(self, cr, uid, ids, field_names, arg, context=None):
        res = dict([(i, {}) for i in ids])
        account_tax_obj = self.pool.get('account.tax')

        self.price_by_product_multi(cr, uid, ids)
        for line in self.browse(cr, uid, ids, context=context):
            for f in field_names:
                if f == 'price_subtotal':
                    if line.discount != 0.0:
                        res[line.id][f] = line.price_unit * line.qty * (1 - (line.discount or 0.0) / 100.0)
                    else:
                        res[line.id][f] = line.price_unit * line.qty
                elif f == 'price_subtotal_incl':
                    taxes = [t for t in line.product_id.taxes_id]
                    if line.qty == 0.0:
                        res[line.id][f] = 0.0
                        continue
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    computed_taxes = account_tax_obj.compute_all(cr, uid, taxes, price, line.qty)
                    cur = line.order_id.pricelist_id.currency_id
                    res[line.id][f] = self.pool.get('res.currency').round(cr, uid, cur, computed_taxes['total'])
        return res

    def price_by_product_multi(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = {}.fromkeys(ids, 0.0)
        lines = self.browse(cr, uid, ids, context=context)

        pricelist_ids = [line.order_id.pricelist_id.id for line in lines]
        products_by_qty_by_partner = [(line.product_id.id, line.qty, line.order_id.partner_id.id) for line in lines]

        price_get_multi_res = self.pool.get('product.pricelist').price_get_multi(cr, uid, pricelist_ids, products_by_qty_by_partner, context=context)

        for line in lines:
            pricelist = line.order_id.pricelist_id.id
            product_id = line.product_id

            if not product_id:
                res[line.id] = 0.0
                continue
            if not pricelist:
                raise osv.except_osv(_('No Pricelist !'),
                    _('You have to select a pricelist in the sale form !\n' \
                    'Please set one before choosing a product.'))

            #old_price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist], product_id.id, qty or 1.0, partner_id, {'uom': uom_id})[pricelist]
            #print "prod_id: %s, pricelist: %s, price: %s" % (product_id.id, pricelist, price)
            price = price_get_multi_res[line.product_id.id][pricelist]
            #print "prod_id: %s, pricelist: %s, price2: %s" % (product_id.id, pricelist, price2)

            #if old_price != price:
            #    raise Exception('old_price != price')

            unit_price = price or product_id.list_price
            res[line.id] = unit_price
            if unit_price is False:
                raise osv.except_osv(_('No valid pricelist line found !'),
                    _("Couldn't find a pricelist line matching this product" \
                    " and quantity.\nYou have to change either the product," \
                    " the quantity or the pricelist."))
        return res

    def price_by_product(self, cr, uid, ids, pricelist, product_id, qty=0, partner_id=False):
        if not product_id:
            return 0.0
        if not pricelist:
            raise osv.except_osv(_('No Pricelist !'),
                _('You have to select a pricelist in the sale form !\n' \
                'Please set one before choosing a product.'))
        p_obj = self.pool.get('product.product').browse(cr, uid, [product_id])[0]
        uom_id = p_obj.uom_po_id.id
        price = self.pool.get('product.pricelist').price_get(cr, uid,
            [pricelist], product_id, qty or 1.0, partner_id, {'uom': uom_id})[pricelist]
        unit_price=price or p_obj.list_price
        if unit_price is False:
            raise osv.except_osv(_('No valid pricelist line found !'),
                _("Couldn't find a pricelist line matching this product" \
                " and quantity.\nYou have to change either the product," \
                " the quantity or the pricelist."))
        return unit_price

    def onchange_product_id(self, cr, uid, ids, pricelist, product_id, qty=0, partner_id=False):
        price = self.price_by_product(cr, uid, ids, pricelist, product_id, qty, partner_id)
        self.write(cr, uid, ids, {'price_unit':price})
        pos_stot = (price * qty)
        return {'value': {'price_unit': price, 'price_subtotal_incl': pos_stot}}

    def onchange_subtotal(self, cr, uid, ids, discount, price, pricelist, qty,partner_id, product_id, *a):
        prod_obj = self.pool.get('product.product')
        price_f = self.price_by_product(cr, uid, ids, pricelist, product_id, qty, partner_id)
        prod_id = ''
        if product_id:
            prod_id = prod_obj.browse(cr, uid, product_id).disc_controle
        disc = 0.0
        if (disc != 0.0 or prod_id) and price_f > 0:
            disc = 100 - (price/price_f*100)
            return {'value': {'discount': disc, 'price_unit': price_f}}
        return {}

    def onchange_ded(self, cr, uid, ids, val_ded, price_u, *a):
        res_obj = self.pool.get('res.users')
        comp = res_obj.browse(cr, uid, uid).company_id.company_discount or 0.0
        val = 0.0
        if val_ded and price_u:
            val=100.0 * val_ded / price_u
        if val > comp:
            return {'value': {'discount': val, 'notice': '' }}
        return {'value': {'discount': val}}

    def onchange_discount(self, cr, uid, ids, discount, price, *a):
        pos_order = self.pool.get('pos.order.line')
        res_obj = self.pool.get('res.users')
        company_disc = pos_order.browse(cr,uid,ids)
        if discount:
            if not company_disc:
                comp=res_obj.browse(cr,uid,uid).company_id.company_discount or 0.0
            else:
                comp= company_disc[0] and company_disc[0].order_id.company_id and  company_disc[0].order_id.company_id.company_discount  or 0.0

            if discount > comp :
                return {'value': {'notice': '', 'price_ded': price * discount * 0.01 or 0.0  }}
            else:
                return {'value': {'notice': 'Minimum Discount', 'price_ded': price * discount * 0.01 or 0.0  }}
        else :
            return {'value': {'notice': 'No Discount', 'price_ded': price * discount * 0.01 or 0.0}}

    def onchange_qty(self, cr, uid, ids, discount, qty, price, context=None):
        subtotal = qty * price
        if discount:
            subtotal = subtotal - (subtotal * discount / 100)
        return {'value': {'price_subtotal_incl': subtotal}}

    _columns = {
        'name': fields.char('Line Description', size=512),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'notice': fields.char('Discount Notice', size=128, required=True),
        'serial_number': fields.char('Serial Number', size=128),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True, change_default=True),
        'price_unit': fields.function(_get_amount, method=True, string='Unit Price', store=True),
        'price_ded': fields.float('Discount(Amount)', digits_compute=dp.get_precision('Point Of Sale')),
        'qty': fields.float('Quantity'),
        'qty_rfd': fields.float('Refunded Quantity'),
        'price_subtotal': fields.function(_amount_line_all, method=True, multi='pos_order_line_amount', string='Subtotal w/o Tax'),
        'price_subtotal_incl': fields.function(_amount_line_all, method=True, multi='pos_order_line_amount', string='Subtotal'),
        'discount': fields.float('Discount (%)', digits=(16, 2)),
        'order_id': fields.many2one('pos.order', 'Order Ref', ondelete='cascade'),
        'create_date': fields.datetime('Creation Date', readonly=True),
        'prodlot_id': fields.many2one('stock.production.lot', 'Production Lot', help="You can specify Production lot for stock move created when you validate the pos order"),
    }

    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'pos.order.line'),
        'qty': lambda *a: 1,
        'discount': lambda *a: 0.0,
        'price_ded': lambda *a: 0.0,
        'notice': lambda *a: 'No Discount',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        }

    def create(self, cr, user, vals, context=None):
        if vals.get('product_id'):
            return super(pos_order_line, self).create(cr, user, vals, context=context)
        return False

    def write(self, cr, user, ids, values, context=None):
        if 'product_id' in values and not values['product_id']:
            return False
        return super(pos_order_line, self).write(cr, user, ids, values, context=context)

    def _scan_product(self, cr, uid, ean, qty, order):
        # search pricelist_id
        product_obj = self.pool.get('product.product')
        pricelist_id = self.pool.get('pos.order').read(cr, uid, [order], ['pricelist_id'] )
        if not pricelist_id:
            return False

        new_line = True

        product_id = product_obj.search(cr, uid, [('ean13','=', ean)])
        if not product_id:
           return False

        # search price product
        product = product_obj.read(cr, uid, product_id)
        product_name = product[0]['name']
        price = self.price_by_product(cr, uid, 0, pricelist_id[0]['pricelist_id'][0], product_id[0], 1)

        order_line_ids = self.search(cr, uid, [('name', '=', product_name), ('order_id', '=' ,order)])
        if order_line_ids:
            new_line = False
            order_line_id = order_line_ids[0]
            qty += self.read(cr, uid, order_line_ids[0], ['qty'])['qty']

        if new_line:
            vals = {'product_id': product_id[0],
                    'price_unit': price,
                    'qty': qty,
                    'name': product_name,
                    'order_id': order,
            }
            line_id = self.create(cr, uid, vals)
            if not line_id:
                raise osv.except_osv(_('Error'), _('Create line failed !'))
        else:
            vals = {
                'qty': qty,
                'price_unit': price
            }
            line_id = self.write(cr, uid, order_line_id, vals)
            if not line_id:
                raise osv.except_osv(_('Error'), _('Modify line failed !'))
            line_id = order_line_id

        price_line = float(qty) * float(price)
        return {
            'name': product_name,
            'product_id': product_id[0],
            'price': price,
            'price_line': price_line ,
            'qty': qty
        }

pos_order_line()

class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'income_pdt': fields.boolean('Product for Input'),
        'expense_pdt': fields.boolean('Product for expenses'),
        'am_out': fields.boolean('Control for Output Operations'),
        'disc_controle': fields.boolean('Discount Control'),
    }
    _defaults = {
        'disc_controle': True,
    }
product_product()

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    _columns = {
        'pos_order': fields.many2one('pos.order', 'Pos order'),
    }

stock_picking()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
