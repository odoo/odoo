# -*- encoding: utf-8 -*-
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

import time
import netsvc
from osv import fields, osv
from mx import DateTime
from tools.translate import _
from decimal import Decimal
import tools
import re


class pos_config_journal(osv.osv):
    _name = 'pos.config.journal'
    _description = "Point of Sale journal configuration."
    _columns = {
        'name': fields.char('Description', size=64),
        'code': fields.char('Code', size=64),
        'journal_id': fields.many2one('account.journal', "Journal")
    }

pos_config_journal()

class res_mode_contact(osv.osv):
    _name = "res.mode.contact"
    _description = "Contact mode"
    _columns={
        'name': fields.char('Mode', size=64, select=1),
        'active': fields.boolean('Active', select=2),
    }
res_mode_contact()

class contact_mode_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'contact_mode_id': fields.many2one('res.mode.contact','Contact Mode'),
     }
contact_mode_partner()


class pos_company_discount(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'company_discount': fields.float('Max Discount(%)', digits=(16,2)),
        'max_diff': fields.float('Max Difference for Cashboxes', digits=(16,2)),
        'account_receivable': fields.many2one('account.account',
            'Default Receivable', required=True, states={'draft': [('readonly', False)]}),
     }

pos_company_discount()


class pos_order(osv.osv):
    _name = "pos.order"
    _description = "Point of Sale"
    _order = "date_order, create_date desc"
    _order = "date_order desc"

    def unlink(self, cr, uid, ids, context={}):
        for rec in self.browse(cr, uid, ids, context=context):
            for rec_statement in rec.statement_ids:
                if (rec_statement.statement_id and rec_statement.statement_id.state=='confirm') or rec.state=='done':
                    raise osv.except_osv(_('Invalid action !'), _('Cannot delete a point of sale which is closed or contains confirmed cashboxes!'))
        return super(pos_order, self).unlink(cr, uid, ids, context=context)

    def onchange_partner_pricelist(self, cr, uid, ids, part, context={}):
        if not part:
            return {}
        pricelist = self.pool.get('res.partner').browse(cr, uid, part).property_product_pricelist.id
        return {'value':{'pricelist_id': pricelist}}

    def _amount_total(self, cr, uid, ids, field_name, arg, context):
        id_set = ",".join(map(str, ids))
        cr.execute("""
        SELECT
            p.id,
            COALESCE(SUM(
                l.price_unit*l.qty*(1-(l.discount/100.0)))::decimal(16,2), 0
                ) AS amount
        FROM pos_order p
            LEFT OUTER JOIN pos_order_line l ON (p.id=l.order_id)
        WHERE p.id IN (""" + id_set  +""") GROUP BY p.id """)
        res = dict(cr.fetchall())
        for rec in self.browse(cr, uid, ids, context):
            if rec.partner_id \
               and rec.partner_id.property_account_position \
               and rec.partner_id.property_account_position.tax_ids:
                res[rec.id] = res[rec.id] - rec.amount_tax
            else :
                res[rec.id] = res[rec.id] + rec.amount_tax
        return res

    def _get_date_payment2(self, cr, uid, ids, context, *a):
        res = {}
        pay_obj = self.pool.get('account.bank.statement')
        stat_obj_line = self.pool.get('account.bank.statement.line')
        tot =0.0
        val=None
        for order in self.browse(cr, uid, ids):
            cr.execute("select date_payment2 from pos_order where id=%d"%(order.id))
            date_p=cr.fetchone()
            date_p=date_p and date_p[0] or None
            if date_p:
                res[order.id]=date_p
                return res
            cr.execute(" SELECT max(l.date) from account_move_line l, account_move m, account_invoice i, account_move_reconcile r, pos_order o where i.move_id=m.id and l.move_id=m.id and l.reconcile_id=r.id and o.id=%d and o.invoice_id=i.id"%(order.id))
            val=cr.fetchone()
            val= val and val[0] or None
            if not val:
                cr.execute("select max(date) from account_bank_statement_line l, account_bank_statement_reconcile s where l.pos_statement_id=%d and l.reconcile_id=s.id"%(order.id))
                val=cr.fetchone()
                val=val and val[0] or None
            if val:
                res[order.id]=val
        return res
    def _get_date_payment(self, cr, uid, ids, context, *a):
        res = {}
        pay_obj = self.pool.get('pos.payment')
        tot =0.0
        val=None
        for order in self.browse(cr, uid, ids):
            cr.execute("select date_payment from pos_order where id=%d"%(order.id))
            date_p=cr.fetchone()
            date_p=date_p and date_p[0] or None
            if date_p:
                res[order.id]=date_p
                return res
            discount_allowed=order.company_id.company_discount
            for line in order.lines:
                if line.discount > discount_allowed:
                    return {order.id: None }
            if order.amount_paid == order.amount_total and not date_p:
                cr.execute("select max(date) from account_bank_statement_line where pos_statement_id=%d"%(order.id))
                val=cr.fetchone()
                val=val and val[0] or None
            if order.invoice_id and order.invoice_id.move_id and not date_p and not val:
                for o in order.invoice_id.move_id.line_id:
                    if o.balance==0:
                        if val<o.date_created:
                            val=o.date_created
            if val:
             #   cr.execute("Update pos_order set date_payment='%s' where id = %d"%(val, order.id))
             #   cr.commit()
                res[order.id]=val
        return res
 #       tax_obj = self.pool.get('account.tax')
 #       pay_obj = self.pool.get('pos.payment')
 #       for order in self.browse(cr, uid, ids):
 #           val = 0.0
 #           tot =0.0
 #           for pay in order.payments:
 #               tot+= pay.amount
 #           if order.amount_total==tot:
 #               res[order.id]=time.strftime('%Y-%m-%d')
 #           for line in order.lines:

 #               val = reduce(lambda x, y: x+round(y['amount'], 2),
 #                       tax_obj.compute_inv(cr, uid, line.product_id.taxes_id,
 #                           line.price_unit * \
 #                           (1-(line.discount or 0.0)/100.0), line.qty),
 #                           val)

 #           res[order.id] = val

    def _amount_tax(self, cr, uid, ids, field_name, arg, context):
        res = {}
        tax_obj = self.pool.get('account.tax')
        for order in self.browse(cr, uid, ids):
            val = 0.0
            for line in order.lines:
                if order.price_type!='tax_excluded':
                    val = reduce(lambda x, y: x+round(y['amount'], 2),
                        tax_obj.compute_inv(cr, uid, line.product_id.taxes_id,
                            line.price_unit * \
                            (1-(line.discount or 0.0)/100.0), line.qty),
                            val)
                else:
                    val = reduce(lambda x, y: x+round(y['amount'], 2),
                        tax_obj.compute(cr, uid, line.product_id.taxes_id,
                            line.price_unit * \
                            (1-(line.discount or 0.0)/100.0), line.qty),
                            val)

            res[order.id] = val
        return res

    def _total_payment(self, cr, uid, ids, field_name, arg, context):
        res = {}
        i=0
        for order in self.browse(cr, uid, ids):
            val = 0.0
            for payment in order.statement_ids:
                val += payment.amount
            res[order.id] = val
            return res
        return {order.id:val}

    def _total_return(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for order in self.browse(cr, uid, ids):
            val = 0.0
            for payment in order.payments:
                val += (payment.amount < 0 and payment.amount or 0)
            res[order.id] = val
        return res

    def payment_get(self, cr, uid, ids, context=None):
        cr.execute("select id from pos_payment where order_id in (%s)" % \
                    ','.join([str(i) for i in ids]))
        return [i[0] for i in cr.fetchall()]

    def _sale_journal_get(self, cr, uid, context):
        journal_obj = self.pool.get('account.journal')
        res = journal_obj.search(cr, uid,
            [('type', '=', 'sale')], limit=1)
        if res:
            return res[0]
        else:
            return False

    def _shop_get(self, cr, uid, context):
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        res = self.pool.get('sale.shop').search(cr, uid, [])
       # res = self.pool.get('sale.shop').search(cr, uid, [('company_id', '=', company.id)])
        if res:
            return res[0]
        else:
            return False

    def _receivable_get(self, cr, uid, context=None):
        prop_obj = self.pool.get('ir.property')
        res = prop_obj.get(cr, uid, 'property_account_receivable', 'res.partner', context=context)
        return res

    def copy(self, cr, uid, id, default=None, context={}):
        if not default:
            default = {}
        default.update({
            'state': 'draft',
            'payments': [],
            'partner_id': False,
            'invoice_id': False,
            'account_move': False,
            'last_out_picking': False,
            'nb_print': 0,
            'pickings': []
        })
        return super(pos_order, self).copy(cr, uid, id, default, context)

    def _get_v( self, cr, uid, ids,*a):
        flag=False
        res_company = self.pool.get('res.company')
        res_obj = self.pool.get('res.users')
        company_disc=self.browse(cr,uid,ids)
        if not company_disc:
            comp=res_obj.browse(cr,uid,uid).company_id.company_discount or 0.0
        else:
            comp= company_disc[0] and company_disc[0].company_id and  company_disc[0].company_id.company_discount  or 0.0
        cr.execute("select discount from pos_order_line where order_id=%s and discount <= %s"%(ids[0],comp))
        res=cr.fetchone()
        cr.execute("select discount from pos_order_line where order_id=%s and discount > %s"%(ids[0],comp))
        res2=cr.fetchone()
        cr.execute("select journal_id from account_bank_statement_line where pos_statement_id=%s "%(ids[0]))
        res3=cr.fetchall()
        list_jrnl=[]
        for r in res3:
            cr.execute("select id from account_journal where name= '%s' and special_journal='t'"%(r[0]))
            res3=cr.fetchone()
            is_special=res3 and res3[0] or None
            if is_special:
                list_jrnl.append(is_special)
        r = {}
        for order in self.browse(cr, uid, ids):
            if order.state in ('paid','done','invoiced') and res and not res2 and not len(list_jrnl):
                r[order.id] = 'accepted'
        return r

    _columns = {
        'name': fields.char('Order Description', size=64, required=True,
            states={'draft': [('readonly', False)]}, readonly=True),
        'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
        'num_sale': fields.char('Internal Note', size=64),
        'shop_id': fields.many2one('sale.shop', 'Shop', required=True,
            states={'draft': [('readonly', False)]}, readonly=True),
        'date_order': fields.datetime('Date Ordered', readonly=True),
        'date_payment': fields.function(_get_date_payment, method=True, string='Validation Date', type='date',  store=True),
        'date_payment2': fields.function(_get_date_payment2, method=True, string='Payment Date', type='date',  store=True),
        'date_validity': fields.date('Validity Date', required=True),
        'user_id': fields.many2one('res.users', 'Connected Salesman', readonly=True),
        'user_id1': fields.many2one('res.users', 'Salesman', required=True),
        'user_id2': fields.many2one('res.users', 'Salesman Manager'),
        'amount_tax': fields.function(_amount_tax, method=True, string='Taxes'),
        'amount_total': fields.function(_amount_total, method=True, string='Total'),
        'amount_paid': fields.function(_total_payment, 'Paid', states={'draft': [('readonly', False)]}, readonly=True, method=True),
        'amount_return': fields.function(_total_return, 'Returned', method=True),
        'lines': fields.one2many('pos.order.line', 'order_id', 'Order Lines', states={'draft': [('readonly', False)]}, readonly=True),
        'price_type': fields.selection([
            ('tax_excluded','Tax excluded')
        ], 'Price method', required=True),
        'statement_ids': fields.one2many('account.bank.statement.line','pos_statement_id','Payments'),
        'payments': fields.one2many('pos.payment', 'order_id', 'Order Payments', states={'draft': [('readonly', False)]}, readonly=True),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', required=True, states={'draft': [('readonly', False)]}, readonly=True),
        'partner_id': fields.many2one( 'res.partner', 'Customer', change_default=True, select=1, states={'draft': [('readonly', False)], 'paid': [('readonly', False)]}),
        'state': fields.selection([('draft', 'Draft'), ('payment', 'Payment'),
                                    ('advance','Advance'),
                                   ('paid', 'Paid'), ('done', 'Done'), ('invoiced', 'Invoiced'), ('cancel', 'Cancel')],
                                  'State', readonly=True, ),
        'invoice_id': fields.many2one('account.invoice', 'Invoice'),
        'account_move': fields.many2one('account.move', 'Account Entry', readonly=True),
        'pickings': fields.one2many('stock.picking', 'pos_order', 'Picking', readonly=True),
        'last_out_picking': fields.many2one('stock.picking', 'Last Output Picking', readonly=True),
        'first_name': fields.char('First Name', size=64),
        'state_2': fields.function(_get_v,type='selection',selection=[('to_verify', 'To Verify'), ('accepted', 'Accepted'),
            ('refused', 'Refused')], string='State', readonly=True, method=True, store=True),
        
    #    'last_name': fields.char('Last Name', size=64),
    #    'street': fields.char('Street', size=64),
    #    'zip2': fields.char('Zip', size=64),
    #    'city': fields.char('City', size=64),
    #    'mobile': fields.char('Mobile', size=64),
    #    'email': fields.char('Email', size=64),
        'note': fields.text('Internal Notes'),
        'nb_print': fields.integer('Number of Print', readonly=True),
        'sale_journal': fields.many2one('account.journal', 'Journal', required=True, states={'draft': [('readonly', False)]}, readonly=True, ),
      #  'account_receivable': fields.many2one('account.account',
      #      'Default Receivable', required=True, states={'draft': [('readonly', False)]},
      #      readonly=True, ),
        'invoice_wanted': fields.boolean('Create Invoice'),
        'note_2': fields.char('Customer Note',size=64),
        'type_rec': fields.char('Type of Receipt',size=64),
        'remboursed': fields.boolean('Remboursed'),
        'contract_number': fields.char('Contract Number', size=512, select=1),
        'journal_entry': fields.boolean('Journal Entry'),
    }


    def _select_pricelist(self, cr, uid, context):
        pricelist = self.pool.get('product.pricelist').search(cr, uid, [('name', '=', 'Public Pricelist')])
        if pricelist:
            return pricelist[0]
        else:
            return False

    def _journal_default(self, cr, uid, context={}):
        journal_list = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'cash')])
        if journal_list:
            return journal_list[0]
        else:
            return False

    _defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'user_id2': lambda self, cr, uid, context: uid,
        'state': lambda *a: 'draft',
        'price_type': lambda *a: 'tax_excluded',
        'state_2': lambda *a: 'to_verify',
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'pos.order'),
        'date_order': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'date_validity': lambda *a: (DateTime.now() + DateTime.RelativeDateTime(months=+6)).strftime('%Y-%m-%d'),
        'nb_print': lambda *a: 0,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        'sale_journal': _sale_journal_get,
        'invoice_wanted': lambda *a: False,
        'shop_id': _shop_get,
        'pricelist_id': _select_pricelist,
    }


    def test_order_lines(self, cr, uid, order, context={}):
        if not order.lines:
            raise osv.except_osv(_('Error'), _('No order lines defined for this sale.'))

        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'pos.order', order.id, 'paid', cr)
        return True

    def dummy_button(self, cr, uid, order, context={}):
        return True

    def test_paid(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context):
            if order.lines and not order.amount_total:
                return True
            if (not order.lines) or (not order.statement_ids) or \
                Decimal(str(order.amount_total))!=Decimal(str(order.amount_paid)):
                return False
        return True

    def _get_qty_differences(self, orders, old_picking):
        """check if the customer changed the product quantity"""
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
        new_picking = picking_model.browse(cr, uid, new_picking_id, context)

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

    def create_picking(self, cr, uid, ids, context={}):
        """Create a picking for each order and validate it."""
        picking_obj = self.pool.get('stock.picking')

        orders = self.browse(cr, uid, ids, context)
        for order in orders:
            if not order.last_out_picking:
                new = True
                picking_id = picking_obj.create(cr, uid, {
                    'origin': order.name,
                    'type': 'out',
                    'state': 'draft',
                    'move_type': 'direct',
                    'note': 'POS notes ' + (order.note or ""),
                    'invoice_state': 'none',
                    'auto_picking': True,
                    'pos_order': order.id,
                    })
                self.write(cr, uid, [order.id], {'last_out_picking': picking_id})
            else:
                picking_id = order.last_out_picking.id
                picking_obj.write(cr, uid, [picking_id], {'auto_picking': True})
                picking = picking_obj.browse(cr, uid, [picking_id], context)[0]
                new = False

                # split the picking (if product quantity has changed):
                diff_dict = self._get_qty_differences(orders, picking)
                if diff_dict:
                    self._split_picking(cr, uid, ids, context, picking, diff_dict)

            if new:
                for line in order.lines:
                    if line.product_id and line.product_id.type=='service':
                        continue
                    prop_ids = self.pool.get("ir.property").search(cr, uid, [('name', '=', 'property_stock_customer')])
                    val = self.pool.get("ir.property").browse(cr, uid, prop_ids[0]).value
                    cr.execute("select s.id from stock_location s, stock_warehouse w where w.lot_stock_id=s.id and w.id= %d "%(order.shop_id.warehouse_id.id))
                    res=cr.fetchone()
                    location_id=res and res[0] or None
#                    location_id = order and order.shop_id and order.shop_id.warehouse_id and order.shop_id.warehouse_id.lot_stock_id.id or None
                    stock_dest_id = int(val.split(',')[1])
                    if line.qty < 0:
                        location_id, stock_dest_id = stock_dest_id, location_id

                    self.pool.get('stock.move').create(cr, uid, {
                        'name': 'Stock move (POS %d)' % (order.id, ),
                        'product_uom': line.product_id.uom_id.id,
                        'product_uos': line.product_id.uom_id.id,
                        'picking_id': picking_id,
                        'product_id': line.product_id.id,
                        'product_uos_qty': abs(line.qty),
                        'product_qty': abs(line.qty),
                        'tracking_id': False,
                        'state': 'waiting',
                        'location_id': location_id,
                        'location_dest_id': stock_dest_id,
                    })

            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
            self.pool.get('stock.picking').force_assign(cr, uid, [picking_id], context)

        return True

    def set_to_draft(self, cr, uid, ids, *args):
        if not len(ids):
            return False

        self.write(cr, uid, ids, {'state': 'draft'})

        wf_service = netsvc.LocalService("workflow")
        for i in ids:
            wf_service.trg_create(uid, 'pos.order', i, cr)
        return True

    def button_invalidate(self, cr, uid, ids, *args):
        res_obj = self.pool.get('res.company')
        try:
            part_company=res_obj.browse(cr,uid,uid) and res_obj.browse(cr,uid,uid).parent_id and res_obj.browse(cr,uid,uid).parent_id.id or None
        except Exception, e:
            raise osv.except_osv(_('Error'), _('You don\'t have enough access to validate this sale!'))
        if part_company:
            raise osv.except_osv(_('Error'), _('You don\'t have enough access to validate this sale!'))
        return True

    def button_validate(self, cr, uid, ids, *args):
        res_obj = self.pool.get('res.company')
        try:
            part_company=res_obj.browse(cr,uid,uid) and res_obj.browse(cr,uid,uid).parent_id and res_obj.browse(cr,uid,uid).parent_id.id or None
        except Exception, e:
            raise osv.except_osv(_('Error'), _('You don\'t have enough access to validate this sale!'))
        if part_company:
            raise osv.except_osv(_('Error'), _('You don\'t have enough access to validate this sale!'))
        for order in self.browse(cr, uid, ids):
            if not order.date_payment:
                cr.execute("select max(date) from account_bank_statement_line where pos_statement_id=%d"%(order.id))
                val=cr.fetchone()
                val=val and val[0] or None
                if val:
                    cr.execute("Update pos_order set date_payment='%s' where id = %d"%(val, order.id))
                    cr.commit()
        return True


    def cancel_order(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'})
        self.cancel_picking(cr, uid, ids, context={})
        return True

    def add_payment(self, cr, uid, order_id, data, context=None):
        """Create a new payment for the order"""
        res_obj = self.pool.get('res.company')
        statementl_obj = self.pool.get('account.bank.statement.line')
        prod_obj = self.pool.get('product.product')
        flag=''
        curr_c=self.pool.get('res.users').browse(cr, uid, uid).company_id
        curr_company=curr_c.id
        order = self.browse(cr, uid, order_id, context)
        if not order.num_sale and data['num_sale']:
            self.write(cr,uid,order_id,{'num_sale': data['num_sale']})
        ids_new=[]
        if order.invoice_wanted and not order.partner_id:
            raise osv.except_osv(_('Error'), _('Cannot create invoice without a partner.'))
        args = {
            'amount': data['amount'],
            }
        if 'payment_date' in data.keys():
            args['date'] = data['payment_date']
        if 'payment_name' in data.keys():
            args['name'] = data['payment_name'] + ' ' +order.name
        account_def = self.pool.get('ir.property').get(cr, uid, 'property_account_receivable', 'res.partner', context=context)
        args['account_id'] = order.partner_id and order.partner_id.property_account_receivable and order.partner_id.property_account_receivable.id or account_def or curr_c.account_receivable.id
        if data.get('is_acc',False):
            args['is_acc']=data['is_acc']
            args['account_id']= prod_obj.browse(cr,uid, data['product_id']).property_account_income and prod_obj.browse(cr,uid, data['product_id']).property_account_income.id
            if not args['account_id']:
                raise osv.except_osv(_('Error'), _('Please provide an account for the product: %s')%(prod_obj.browse(cr,uid, data['product_id']).name))
        args['partner_id'] = order.partner_id and order.partner_id.id or None
        args['ref'] = order.contract_number or None

        statement_obj= self.pool.get('account.bank.statement')
        statement_id = statement_obj.search(cr,uid, [
                                                     ('journal_id', '=', data['journal']),
                                                     ('company_id', '=', curr_company),
                                                     ('user_id', '=', uid),
                                                     ('state', '=', 'open')])
        if len(statement_id)==0:
            raise osv.except_osv(_('Error !'), _('You have to open at least one cashbox'))
        if statement_id:
            statement_id=statement_id[0]
        args['statement_id']= statement_id
        args['pos_statement_id']= order_id
        args['journal_id']= data['journal']
        statement_line_id = self.pool.get('account.bank.statement.line').create(cr, uid, args)
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
            })
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_write(uid, 'pos.order', order_id, cr)

        return order_line_id

    def refund(self, cr, uid, ids, context={}):
        clone_list = []
        line_obj = self.pool.get('pos.order.line')

        for order in self.browse(cr, uid, ids):
            clone_id = self.copy(cr, uid, order.id, {
                'name': order.name + ' REFUND',
                'date_order': time.strftime('%Y-%m-%d'),
                'state': 'draft',
                'note': 'REFUND\n'+ (order.note or ''),
                'invoice_id': False,
                'nb_print': 0,
                'statement_ids': False,
                })
            clone_list.append(clone_id)


        for clone in self.browse(cr, uid, clone_list):
            for order_line in clone.lines:
                line_obj.write(cr, uid, [order_line.id], {
                    'qty': -order_line.qty
                    })
        return clone_list

    def action_invoice(self, cr, uid, ids, context={}):
        res_obj = self.pool.get('res.company')
        inv_ref = self.pool.get('account.invoice')
        inv_line_ref = self.pool.get('account.invoice.line')
        inv_ids = []

        for order in self.browse(cr, uid, ids, context):
            curr_c = order.user_id1.company_id
            if order.invoice_id:
                inv_ids.append(order.invoice_id.id)
                continue

            if not order.partner_id:
                raise osv.except_osv(_('Error'), _('Please provide a partner for the sale.'))

            cr.execute('select a.id from account_account a, res_company p where p.account_receivable=a.id and p.id=%s', (curr_c.id, ))
            res=cr.fetchone()
            acc=res and res[0] or None
            inv = {
                'name': 'Invoice from POS: '+order.name,
                'origin': order.name,
                'account_id':acc,
                'journal_id':order.sale_journal.id or None,
                'type': 'out_invoice',
                'reference': order.name,
                'partner_id': order.partner_id.id,
                'comment': order.note or '',
            }
            inv.update(inv_ref.onchange_partner_id(cr, uid, [], 'out_invoice', order.partner_id.id)['value'])
            if not inv.get('account_id', None):
                inv['account_id'] = acc
            inv_id = inv_ref.create(cr, uid, inv, context)

            self.write(cr, uid, [order.id], {'invoice_id': inv_id, 'state': 'invoiced'})
            inv_ids.append(inv_id)
            for line in order.lines:
                inv_line = {
                    'invoice_id': inv_id,
                    'product_id': line.product_id.id,
                    'quantity': line.qty,
                }
                inv_line.update(inv_line_ref.product_id_change(cr, uid, [],
                                                               line.product_id.id,
                                                               line.product_id.uom_id.id,
                                                               line.qty, partner_id = order.partner_id.id, fposition_id=order.partner_id.property_account_position.id)['value'])
                inv_line['price_unit'] = line.price_unit
                inv_line['discount'] = line.discount
                inv_line['account_id'] = acc

                inv_line['invoice_line_tax_id'] = ('invoice_line_tax_id' in inv_line)\
                    and [(6, 0, inv_line['invoice_line_tax_id'])] or []
                inv_line_ref.create(cr, uid, inv_line, context)

        for i in inv_ids:
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'account.invoice', i, 'invoice_open', cr)
        return inv_ids

    def create_account_move(self, cr, uid, ids, context=None):
        account_move_obj = self.pool.get('account.move')
        account_move_line_obj = self.pool.get('account.move.line')
        account_period_obj = self.pool.get('account.period')
        account_tax_obj = self.pool.get('account.tax')
        period = account_period_obj.find(cr, uid, context=context)[0]

        for order in self.browse(cr, uid, ids, context=context):
            curr_c = self.pool.get('res.users').browse(cr, uid, uid).company_id
            comp_id = self.pool.get('res.users').browse(cr, order.user_id.id, order.user_id.id).company_id
            comp_id=comp_id and comp_id.id or False
            to_reconcile = []
            group_tax = {}
            account_def = self.pool.get('ir.property').get(cr, uid, 'property_account_receivable', 'res.partner', context=context)
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
                if order.price_type=='tax_excluded':
                    computed_taxes = account_tax_obj.compute(
                        cr, uid, taxes, line.price_unit, line.qty)
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
                if order.price_type!='tax_excluded':
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
                    'date': order.date_order,
                    'ref': order.contract_number or order.name,
                    'quantity': line.qty,
                    'product_id':line.product_id.id,
                    'move_id': move_id,
                    'account_id': income_account,
                    'company_id': comp_id,
                    'credit': ((amount>0) and amount) or 0.0,
                    'debit': ((amount<0) and -amount) or 0.0,
                    'journal_id': order.sale_journal.id,
                    'period_id': period,
                    'tax_code_id': tax_code_id,
                    'tax_amount': tax_amount,
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
                        'name': "bb"+order.name,
                        'date': order.date_order,
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
                    'name':"cc"+order.name,
                    'date': order.date_order,
                    'ref': order.contract_number or order.name,
                    'move_id': move_id,
                    'company_id': comp_id,
                    'quantity': line.qty,
                    'product_id':line.product_id.id,
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
                'name': "dd"+order.name,
                'date': order.date_order,
                'ref': order.contract_number or order.name,
                'move_id': move_id,
                'company_id': comp_id,
                'account_id': order_account,
                'credit': ((order.amount_total<0) and -order.amount_total)\
                    or 0.0,
                'debit': ((order.amount_total>0) and order.amount_total)\
                    or 0.0,
                'journal_id': order.sale_journal.id,
                'period_id': period,
            }, context=context))


            # search the account receivable for the payments:
            account_receivable = order.sale_journal.default_credit_account_id.id
            if not account_receivable:
                raise  osv.except_osv(_('Error !'),
                    _('There is no receivable account defined for this journal:'\
                    ' "%s" (id:%d)') % (order.sale_journal.name, order.sale_journal.id, ))
            am=0.0
            for payment in order.statement_ids:
                am+=payment.amount

                if am > 0:
                    payment_account = \
                        payment.statement_id.journal_id.default_debit_account_id.id
                else:
                    payment_account = \
                        payment.statement_id.journal_id.default_credit_account_id.id

                # Create one entry for the payment
                if payment.is_acc:
                    continue
                payment_move_id = account_move_obj.create(cr, uid, {
                    'journal_id': payment.statement_id.journal_id.id,
                    'period_id': period,
                }, context=context)

            for stat_l in order.statement_ids:
                if stat_l.is_acc and len(stat_l.move_ids):
                    for st in stat_l.move_ids:
                        for s in st.line_id:
                            if s.credit:
                                account_move_line_obj.copy(cr, uid, s.id, { 'debit': s.credit,
                                                                            'statement_id': False,
                                                                            'credit': s.debit})
                                account_move_line_obj.copy(cr, uid, s.id, {
                                                                        'statement_id': False,
                                                                        'account_id':order_account
                                                                     })
           #     account_move_obj.button_validate(cr, uid, [move_id, payment_move_id], context=context)
            self.write(cr,uid,order.id,{'state':'done'})
         #       account_move_line_obj.reconcile(cr, uid, to_reconcile, type='manual', context=context)
        return True

    def cancel_picking(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            for picking in order.pickings:
                self.pool.get('stock.picking').unlink(cr, uid, [picking.id], context)
        return True


    def action_payment(self, cr, uid, ids, context=None):
        vals = {'state': 'payment'}
        for pos in self.browse(cr, uid, ids):
            create_contract_nb = False
            for line in pos.lines:
                if line.product_id.product_type == 'MD':
                    create_contract_nb = True
                    break
            if create_contract_nb:
                seq = self.pool.get('ir.sequence').get(cr, uid, 'pos.user_%s' % pos.user_id1.login)
                vals['contract_number'] ='%s-%s' % (pos.user_id1.login, seq)
        self.write(cr, uid, ids, vals)

    def action_paid(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if context.get('flag',False):
            self.create_picking(cr, uid, ids, context={})
            self.write(cr, uid, ids, {'state': 'paid'})
        else:
            context['flag']=True
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'})
        return True

    def action_done(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            if not order.journal_entry:
                self.create_account_move(cr, uid, ids, context={})
        #self.write(cr, uid, ids, {'state': 'done'})
        return True

    def compute_state(self, cr, uid, id):
        cr.execute("select act.id, act.name from wkf_activity act "
                   "inner join wkf_workitem item on act.id=item.act_id "
                   "inner join wkf_instance inst on item.inst_id=inst.id "
                   "inner join wkf on inst.wkf_id=wkf.id "
                   "where wkf.osv='pos.order' and inst.res_id=%s "
                   "order by act.name", (id,))
        return [name for id, name in cr.fetchall()]

pos_order()

class account_bank_statement(osv.osv):
    _inherit = 'account.bank.statement'
    _columns={
        'user_id': fields.many2one('res.users',ondelete='cascade',string='User', readonly=True),
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
    _columns={
        'journal_id': fields.function(_get_statement_journal, method=True,store=True, string='Journal', type='char', size=64),
        'am_out':fields.boolean("To count"),
        'is_acc':fields.boolean("Is accompte"),
        'pos_statement_id': fields.many2one('pos.order',ondelete='cascade'),
    }
account_bank_statement_line()

class pos_order_line(osv.osv):
    _name = "pos.order.line"
    _description = "Lines of Point of Sale"

    def _get_amount(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for line in self.browse(cr, uid, ids):
            price = self.price_by_product(cr, uid, ids, line.order_id.pricelist_id.id, line.product_id.id, line.qty, line.order_id.partner_id.id)
            res[line.id]=price
        return res

    def _amount_line_ttc(self, cr, uid, ids, field_name, arg, context):
        res = {}
        account_tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids):
            tax_amount = 0.0
            taxes = [t for t in line.product_id.taxes_id]
            computed_taxes = account_tax_obj.compute(cr, uid, taxes, line.price_unit, line.qty)
            for tax in computed_taxes:
                tax_amount += tax['amount']
            price = self.price_by_product(cr, uid, ids, line.order_id.pricelist_id.id, line.product_id.id, line.qty, line.order_id.partner_id.id)
            if line.discount!=0.0:
                res[line.id] = line.price_unit * line.qty * (1 - (line.discount or 0.0) / 100.0)
            else:
                res[line.id]=line.price_unit*line.qty
            res[line.id] = res[line.id] + tax_amount
            
        return res
    def _amount_line(self, cr, uid, ids, field_name, arg, context):
        res = {}

        for line in self.browse(cr, uid, ids):
            price = self.price_by_product(cr, uid, ids, line.order_id.pricelist_id.id, line.product_id.id, line.qty, line.order_id.partner_id.id)
            if line.discount!=0.0:
                res[line.id] = line.price_unit * line.qty * (1 - (line.discount or 0.0) / 100.0)
#                res[line.id] = price * line.qty * (1 - (line.discount or 0.0) / 100.0)
            else:
                res[line.id]=line.price_unit*line.qty
        return res

    def price_by_product(self, cr, uid, ids, pricelist, product_id, qty=0, partner_id=False):
        if not product_id:
            return 0.0
        if not pricelist:
            raise osv.except_osv(_('No Pricelist !'),
                _('You have to select a pricelist in the sale form !\n' \
                'Please set one before choosing a product.'))
        p_obj = self.pool.get('product.product').browse(cr,uid,product_id).list_price
        price = self.pool.get('product.pricelist').price_get(cr, uid,
            [pricelist], product_id, qty or 1.0, partner_id)[pricelist] 
        if price is False:
            raise osv.except_osv(_('No valid pricelist line found !'),
                _("Couldn't find a pricelist line matching this product" \
                " and quantity.\nYou have to change either the product," \
                " the quantity or the pricelist."))
        return price

    def onchange_product_id(self, cr, uid, ids, pricelist, product_id, qty=0, partner_id=False):
        price = self.price_by_product(cr, uid, ids, pricelist, product_id, qty, partner_id)
        self.write(cr,uid,ids,{'price_unit':price})
        return {'value': {'price_unit': price}, 'qty': 1}

    def onchange_subtotal(self, cr, uid, ids, discount, price, pricelist,qty,partner_id, product_id,*a):
        prod_obj = self.pool.get('product.product')
        price_f = self.price_by_product(cr, uid, ids, pricelist, product_id, qty, partner_id)
        prod_id=''
        if product_id:
            prod_id=prod_obj.browse(cr,uid,product_id).disc_controle
        disc=0.0
        if (disc != 0.0 or prod_id) and price_f>0:
            disc=100-(price/price_f*100)
            return {'value':{'discount':disc, 'price_unit':price_f}}#,'notice':''}}#, 'price_subtotal':(price_f*qty*(1-disc))}}
        return {}

    def onchange_ded(self, cr, uid,ids, val_ded,price_u,*a):
        pos_order = self.pool.get('pos.order.line')
        res_obj = self.pool.get('res.users')
        res_company = self.pool.get('res.company')
        comp = res_obj.browse(cr,uid,uid).company_id.company_discount or 0.0
        val=0.0
        if val_ded and price_u:
            val=100.0*val_ded/price_u
        if val > comp:
            return {'value': {'discount':val, 'notice':'' }}
        return {'value': {'discount':val}}

    def onchange_discount(self, cr, uid,ids, discount,price,*a):
        pos_order = self.pool.get('pos.order.line')
        res_obj = self.pool.get('res.users')
        res_company = self.pool.get('res.company')
        company_disc = pos_order.browse(cr,uid,ids)
        if discount:
            if not company_disc:
                comp=res_obj.browse(cr,uid,uid).company_id.company_discount or 0.0
            else:
                comp= company_disc[0] and company_disc[0].order_id.company_id and  company_disc[0].order_id.company_id.company_discount  or 0.0

            if discount > comp :
                return {'value': {'notice':'','price_ded':price*discount*0.01 or 0.0  }}
            else:
                return {'value': {'notice':'Minimum Discount','price_ded':price*discount*0.01 or 0.0  }}
        else :
            return {'value': {'notice':'No Discount', 'price_ded':price*discount*0.01 or 0.0 }}
    _columns = {
        'name': fields.char('Line Description', size=512),
        'company_id':fields.many2one('res.company', 'Company', required=True),
        'notice': fields.char('Discount Notice', size=128, required=True),
        'serial_number': fields.char('Serial Number', size=128),
#        'contract_number': fields.char('Contract Number', size=512),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True, change_default=True),
#        'price_unit': fields.float('Unit Price'),
        'price_unit': fields.function(_get_amount, method=True, string='Unit Price', store=True),
        'price_ded': fields.float('Discount(Amount)'),
        'qty': fields.float('Quantity'),
        'qty_rfd': fields.float('Refunded Quantity'),
        'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal w/o Tax'),
        'price_subtotal_incl': fields.function(_amount_line_ttc, method=True, string='Subtotal'),
        'discount': fields.float('Discount (%)', digits=(16, 2)),
        'order_id': fields.many2one('pos.order', 'Order Ref', ondelete='cascade'),
        'create_date': fields.datetime('Creation Date', readonly=True),
        }

    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'pos.order.line'),
        'qty': lambda *a: 1,
        'discount': lambda *a: 0.0,
        'price_ded': lambda *a: 0.0,
        'notice': lambda *a: 'No Discount',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        }

    def create(self, cr, user, vals, context={}):
        if vals.get('product_id'):
            return super(pos_order_line, self).create(cr, user, vals, context)
        return False

    def write(self, cr, user, ids, values, context={}):
        if 'product_id' in values and not values['product_id']:
            return False
        return super(pos_order_line, self).write(cr, user, ids, values, context)

    def _scan_product(self, cr, uid, ean, qty, order):
        # search pricelist_id
        pricelist_id = self.pool.get('pos.order').read(cr, uid, [order], ['pricelist_id'] )
        if not pricelist_id:
            return False

        new_line = True

        product_id = self.pool.get('product.product').search(cr, uid, [('ean13','=', ean)])
        if not product_id:
           return False

        # search price product
        product = self.pool.get('product.product').read(cr, uid, product_id)
        product_name = product[0]['name']
        price = self.price_by_product(cr, uid, 0, pricelist_id[0]['pricelist_id'][0], product_id[0], 1)

        order_line_ids = self.search(cr, uid, [('name','=',product_name),('order_id','=',order)])
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
                raise wizard.except_wizard(_('Error'), _('Create line failed !'))
        else:
            vals = {
                'qty': qty,
                'price_unit': price
            }
            line_id = self.write(cr, uid, order_line_id, vals)
            if not line_id:
                raise wizard.except_wizard(_('Error'), _('Modify line failed !'))
            line_id = order_line_id

        price_line = float(qty)*float(price)
        return {'name': product_name, 'product_id': product_id[0], 'price': price, 'price_line': price_line ,'qty': qty }

pos_order_line()


class pos_payment(osv.osv):
    _name = 'pos.payment'
    _description = 'Pos Payment'

    def _journal_get(self, cr, uid, context={}):
        obj = self.pool.get('account.journal')
        ids = obj.search(cr, uid, [('type', '=', 'cash')])
        res = obj.read(cr, uid, ids, ['id', 'name'], context)
        res = [(r['id'], r['name']) for r in res]
        return res

    def _journal_default(self, cr, uid, context={}):
        journal_list = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'cash')])
        if journal_list:
            return journal_list[0]
        else:
            return False

    _columns = {
        'name': fields.char('Description', size=64),
        'order_id': fields.many2one('pos.order', 'Order Ref', required=True, ondelete='cascade'),
        'journal_id': fields.many2one('account.journal', "Journal", required=True),
        'payment_id': fields.many2one('account.payment.term','Payment Term', select=True),
        'payment_nb': fields.char('Piece Number', size=32),
        'payment_name': fields.char('Payment Name', size=32),
        'payment_date': fields.date('Payment Date', required=True),
        'amount': fields.float('Amount', required=True),
    }
    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'pos.payment'),
        'journal_id': _journal_default,
        'payment_date':  lambda *a: time.strftime('%Y-%m-%d'),
    }

    def create(self, cr, user, vals, context={}):
        if vals.get('journal_id') and vals.get('amount'):
            return super(pos_payment, self).create(cr, user, vals, context)
        return False

    def write(self, cr, user, ids, values, context={}):
        if 'amount' in values and not values['amount']:
            return False
        if 'journal_id' in values and not values['journal_id']:
            return False
        return super(pos_payment, self).write(cr, user, ids, values, context)

pos_payment()


class report_transaction_pos(osv.osv):
    _name = "report.transaction.pos"
    _description = "transaction for the pos"
    _auto = False
    _columns = {
        'date_create': fields.char('Date', size=16, readonly=True),
        'journal_id': fields.many2one('account.journal', 'Sales Journal', readonly=True),
        'jl_id': fields.many2one('account.journal', 'Cash Journals', readonly=True),
        'user_id': fields.many2one('res.users', 'User', readonly=True),
        'no_trans': fields.float('Number of Transaction', readonly=True),
        'amount': fields.float('Amount', readonly=True),
        'invoice_id': fields.float('Nbr Invoice', readonly=True),
        'invoice_am': fields.float('Invoice Amount', readonly=True),
        'product_nb': fields.float('Product Nb.', readonly=True),
        'disc': fields.float('Disc.', readonly=True),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_transaction_pos')
        cr.execute("""
            create or replace view report_transaction_pos as (
               select
                    min(absl.id) as id,
                    count(absl.id) as no_trans,
                    sum(absl.amount) as amount,
                    sum(line.price_ded) as disc,
                    to_char(date_trunc('day',absl.create_date),'YYYY-MM-DD')::text as date_create,
                    po.user_id as user_id,
                    po.sale_journal as journal_id,
                    abs.journal_id as jl_id,
                    count(po.invoice_id) as invoice_id,
                    count(p.id) as product_nb
                from
                    account_bank_statement_line as absl,
                    account_bank_statement as abs,
                    product_product as p,
                    pos_order_line as line,
                    pos_order as po
                where
                    absl.pos_statement_id = po.id and
                    line.order_id=po.id and
                    line.product_id=p.id and
                    absl.statement_id=abs.id

                group by
                    po.user_id,po.sale_journal, abs.journal_id,
                    to_char(date_trunc('day',absl.create_date),'YYYY-MM-DD')::text
                )
        """)
                    #to_char(date_trunc('day',absl.create_date),'YYYY-MM-DD')
                    #to_char(date_trunc('day',absl.create_date),'YYYY-MM-DD')::text as date_create,
report_transaction_pos()

class report_sales_by_user_pos(osv.osv):
    _name = "report.sales.by.user.pos"
    _description = "Sales by user"
    _auto = False
    _columns = {
        'date_order': fields.date('Order Date',required=True, select=True),
        'amount': fields.float('Total', readonly=True, select=True),
        'qty': fields.float('Quantity', readonly=True, select=True),
        'user_id': fields.many2one('res.users', 'User', readonly=True, select=True),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_sales_by_user_pos')
        cr.execute("""
            create or replace view report_sales_by_user_pos as (
                select
                    min(po.id) as id,
                    to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::text as date_order,
                    po.user_id as user_id,
                    sum(pol.qty)as qty,
                    sum((pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0))) as amount
                from
                    pos_order as po,pos_order_line as pol,product_product as pp,product_template as pt
                where
                    pt.id=pp.product_tmpl_id and pp.id=pol.product_id and po.id = pol.order_id
               group by
                    to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::text,
                    po.user_id

                )
        """)
report_sales_by_user_pos()

class report_sales_by_user_pos_month(osv.osv):
    _name = "report.sales.by.user.pos.month"
    _description = "Sales by user monthly"
    _auto = False
    _columns = {
        'date_order': fields.date('Order Date',required=True, select=True),
        'amount': fields.float('Total', readonly=True, select=True),
        'qty': fields.float('Quantity', readonly=True, select=True),
        'user_id': fields.many2one('res.users', 'User', readonly=True, select=True),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_sales_by_user_pos_month')
        cr.execute("""
            create or replace view report_sales_by_user_pos_month as (
                select
                    min(po.id) as id,
                    to_char(date_trunc('month',po.date_order),'YYYY-MM-DD')::text as date_order,
                    po.user_id as user_id,
                    sum(pol.qty)as qty,
                    sum((pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0))) as amount
                from
                    pos_order as po,pos_order_line as pol,product_product as pp,product_template as pt
                where
                    pt.id=pp.product_tmpl_id and pp.id=pol.product_id and po.id = pol.order_id
               group by
                    to_char(date_trunc('month',po.date_order),'YYYY-MM-DD')::text,
                    po.user_id

                )
        """)
report_sales_by_user_pos_month()

class report_sales_by_margin_pos(osv.osv):
    _name = "report.sales.by.margin.pos"
    _description = "Sales by margin"
    _auto = False
    _columns = {
#        'pos_name': fields.char('POS Order', size=64, readonly=True),
        'product_name':fields.char('Product Name', size=64, readonly=True),
        'date_order': fields.date('Order Date',required=True, select=True),
        'amount': fields.float('Total', readonly=True, select=True),
        'user_id': fields.many2one('res.users', 'User', readonly=True, select=True),
        'qty': fields.float('Qty', readonly=True, select=True),
        'net_margin_per_qty':fields.float('Net margin per Qty', readonly=True, select=True),
        'total':fields.float('Margin', readonly=True, select=True),

    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_sales_by_margin_pos')
        cr.execute("""
            create or replace view report_sales_by_margin_pos as (
                select
                    min(pol.id) as id,
                    po.user_id as user_id,
                    pt.name as product_name,
                    to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::text as date_order,
                    sum(pol.qty) as qty,
                    pt.list_price-pt.standard_price as net_margin_per_qty,
                    (pt.list_price-pt.standard_price) *sum(pol.qty) as total
                from
                    product_template as pt,
                    product_product as pp,
                    pos_order_line as pol,
                    pos_order as po
                where
                    pol.product_id = pp.product_tmpl_id and
                    pp.product_tmpl_id = pt.id and
                    po.id = pol.order_id

                group by
                    pt.name,
                    pt.list_price,
                    pt.standard_price,
                    po.user_id,
                    to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::text

                )
        """)
report_sales_by_margin_pos()

class report_sales_by_margin_pos_month(osv.osv):
    _name = "report.sales.by.margin.pos.month"
    _description = "Sales by margin monthly"
    _auto = False
    _columns = {
#        'pos_name': fields.char('POS Order', size=64, readonly=True),
        'product_name':fields.char('Product Name', size=64, readonly=True),
        'date_order': fields.date('Order Date',required=True, select=True),
        'amount': fields.float('Total', readonly=True, select=True),
        'user_id': fields.many2one('res.users', 'User', readonly=True, select=True),
        'qty': fields.float('Qty', readonly=True, select=True),
        'net_margin_per_qty':fields.float('Net margin per Qty', readonly=True, select=True),
        'total':fields.float('Margin', readonly=True, select=True),

    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_sales_by_margin_pos_month')
        cr.execute("""
            create or replace view report_sales_by_margin_pos_month as (
                select
                    min(pol.id) as id,
                    po.user_id as user_id,
                    pt.name as product_name,
                    to_char(date_trunc('month',po.date_order),'YYYY-MM-DD')::text as date_order,
                    sum(pol.qty) as qty,
                    pt.list_price-pt.standard_price as net_margin_per_qty,
                    (pt.list_price-pt.standard_price) *sum(pol.qty) as total
                from
                    product_template as pt,
                    product_product as pp,
                    pos_order_line as pol,
                    pos_order as po
                where
                    pol.product_id = pp.product_tmpl_id and
                    pp.product_tmpl_id = pt.id and
                    po.id = pol.order_id

                group by
                    pt.name,
                    pt.list_price,
                    pt.standard_price,
                    po.user_id,
                    to_char(date_trunc('month',po.date_order),'YYYY-MM-DD')::text

                )
        """)
report_sales_by_margin_pos_month()


class account_move_line(osv.osv):
    _inherit = 'account.move.line'
    def create(self, cr, user, vals, context={}):
        pos_obj = self.pool.get('pos.order')
        val_name = vals.get('name', '')
        val_ref = vals.get('ref', '')
        if (val_name and 'POS' in val_name) and (val_ref and 'PACK' in val_ref):
            aaa = re.search(r'Stock move.\((.*)\)', vals.get('name'))
            name_pos = aaa.groups()[0]
            pos_id = name_pos.replace('POS ','')
            if pos_id and pos_id.isdigit():
                pos_curr = pos_obj.browse(cr,user,int(pos_id))
                pos_curr = pos_curr  and pos_curr.contract_number or ''
                vals['ref'] = pos_curr or vals.get('ref')
        return super(account_move_line, self).create(cr, user, vals, context)

account_move_line()


class account_move(osv.osv):
    _inherit = 'account.move'
    def create(self, cr, user, vals, context={}):
        pos_obj = self.pool.get('pos.order')
        val_name = vals.get('name', '')
        val_ref = vals.get('ref', '')
        if (val_name and 'POS' in val_name) and (val_ref and 'PACK' in val_ref):
            aaa = re.search(r'Stock move.\((.*)\)', vals.get('name'))
            name_pos = aaa.groups()[0]
            pos_id = name_pos.replace('POS ','')
            if pos_id and pos_id.isdigit():
                pos_curr = pos_obj.browse(cr,user,int(pos_id))
                pos_curr = pos_curr  and pos_curr.contract_number or ''
                vals['ref'] = pos_curr or vals.get('ref')
        return super(account_move, self).create(cr, user, vals, context)

account_move()


class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'income_pdt': fields.boolean('Product for Incoming'),
        'expense_pdt': fields.boolean('Product for expenses'),
        'am_out': fields.boolean('Controle for Outgoing Operations'),
        'disc_controle': fields.boolean('Discount Controle '),
}
    _defaults = {
        'disc_controle': lambda *a: True,
}
product_product()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
