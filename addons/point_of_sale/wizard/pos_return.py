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

#import wizard
#import pooler
#from tools.misc import UpdateableStr
#
#import netsvc
#import time
#
#from tools.translate import _
#from decimal import Decimal

#arch=UpdateableStr()
#fields={}

import netsvc
from osv import osv,fields
from tools.translate import _
from mx import DateTime
import time


class pos_return(osv.osv_memory):
    _name = 'pos.return'
    _description = 'Point of sale return'

    _columns = {
                
    }
pos_return()

class pos_add_payment(osv.osv_memory):
    _name = 'pos.add.payment'
    _description = 'Add Payment'

    _columns = {
        'amount': fields.float('Amount', digits=(16,2),required=True),
        'journal': fields.function(_get_journal, 'Journal', method=True, required=True),
        'payment_date': fields.date('Payment date',required=True),
        'payment_name': fields.char('Payment name', size=32,required=True),
        'invoice_wanted': fields.boolean('Invoice'),
        'num_sale': fields.char('Num.Cof', size=32)        
    }
    _defaults = {
          'payment_name': lambda *a: 'Payment'
        }

pos_add_payment()

class pos_add_product(osv.osv_memory):
    _name = 'pos.add.product'
    _description = 'Add Product'

    _columns = {
        'product': fields.many2one('product.product','Product', required=True),
        'quantity': fields.integer( 'Quantity',required=True),
             
    }

    _defaults = {
          'product': lambda *a: 'False',
          'quantity': lambda *a: 1
        }

pos_add_product()


def _get_journal(self, cr, uid, context):
    pool = pooler.get_pool(cr.dbname)
    obj = pool.get('account.journal')
    c=pool.get('res.users').browse(cr,uid,uid).company_id.id
    ids = obj.search(cr, uid, [('type', '=', 'cash'), ('company_id','=',c)])
    res = obj.read(cr, uid, ids, ['id', 'name'], context)
    res = [(r['id'], r['name']) for r in res]
    return res


payment_form = """<?xml version="1.0"?>
<form string="Add payment :">
    <field name="amount" />
    <field name="journal"/>
    <field name="payment_date" />
    <field name="payment_name" />
    <field name="invoice_wanted" />
    <field name="num_sale" />
</form>
"""

payment_fields = {
    'amount': {'string': 'Amount', 'type': 'float', 'required': True},
    'invoice_wanted': {'string': 'Invoice', 'type': 'boolean'},
    'journal': {'string': 'Journal',
            'type': 'selection',
            'selection': _get_journal,
            'required': True,
        },
    'payment_date': {'string': 'Payment date', 'type': 'date', 'required': True},
    'payment_name': {'string': 'Payment name', 'type': 'char', 'size': '32', 'required':True, 'default':'Payment'},
    'num_sale': {'string': 'Num.Cof', 'type': 'char', 'size': '32'},
    }


def _pre_init(self, cr, uid, data, context):
    def _get_journal(pool, order):
        j_obj = pool.get('account.journal')

        journal_to_fetch = 'DEFAULT'
        if order.amount_total < 0:
            journal_to_fetch = 'GIFT'
        else:
            if order.amount_paid > 0:
                journal_to_fetch = 'REBATE'

        pos_config_journal = pool.get('pos.config.journal')
        ids = pos_config_journal.search(cr, uid, [('code', '=', journal_to_fetch)])
        objs = pos_config_journal.browse(cr, uid, ids)
        journal=''
        if objs:
            journal = objs[0].journal_id.id
        else:
            existing = [payment.journal_id.id for payment in order.payments]
            ids = j_obj.search(cr, uid, [('type', '=', 'cash')])
            for i in ids:
                if i not in existing:
                    journal = i
                    break
            if not journal:
                journal = ids and ids[0]
        return journal
    pool = pooler.get_pool(cr.dbname)
    order = pool.get('pos.order').browse(cr, uid, data['id'], context)
    # get amount to pay:
#    amount = Decimal(str(order.amount_total)) - Decimal(str(order.amount_paid))
    amount = order.amount_total - order.amount_paid
    if amount <= 0:
        pool.get('pos.order').action_paid(cr, uid, data['ids'], context)

    # get journal:
    journal = _get_journal(pool, order)

    # check if an invoice is wanted:
    #invoice_wanted_checked = not not order.partner_id # not not -> boolean
    invoice_wanted_checked = False

    # select the current date
    current_date = time.strftime('%Y-%m-%d')

    return {'journal': journal, 'amount': amount, 'invoice_wanted': invoice_wanted_checked, 'payment_date': current_date}


def _add_pay(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    order_obj = pool.get('pos.order')
    jrnl_obj = pool.get('account.journal')
    result = data['form']
    invoice_wanted = data['form']['invoice_wanted']
    jrnl_used=False
    if data['form'] and data['form'].get('journal',False):
        jrnl_used=jrnl_obj.browse(cr,uid,data['form']['journal'])

    # add 'invoice_wanted' in 'pos.order'
    order_obj.write(cr, uid, [data['id']], {'invoice_wanted': invoice_wanted})

    order_obj.add_payment(cr, uid, data['id'], result, context=context)
    return {}


def _check(self, cr, uid, data, context):
    """Check the order:
    if the order is not paid: continue payment,
    if the order is paid print invoice (if wanted) or ticket.
    """
    pool = pooler.get_pool(cr.dbname)
    order_obj = pool.get('pos.order')
    order = order_obj.browse(cr, uid, data['id'], context)
    order_obj.test_order_lines(cr, uid, order, context=context)

    action = 'ask_pay'
    if order.state == 'paid':
        if order.partner_id:
            if order.invoice_wanted:
                action = 'invoice'
            else:
                action = 'paid'
        elif order.date_payment:
            action = 'receipt'
        else:
            action='paid'

    if order.amount_total == order.amount_paid:
        order_obj.write(cr,uid,data['ids'],{'state':'done'})
        action = 'receipt'

    return action


def create_invoice(self, cr, uid, data, context):
    wf_service = netsvc.LocalService("workflow")
    for i in data['ids']:
        wf_service.trg_validate(uid, 'pos.order', i, 'invoice', cr)
    return {}



_form = """<?xml version="1.0"?>
<form string="Add product :">
<field name="product"/>
<field name="quantity"/>
</form>
"""
_fields = {
    'product': {
        'string': 'Product',
        'type': 'many2one',
        'relation': 'product.product',
        'required': True,
        'default': False
    },

    'quantity': {
        'string': 'Quantity',
        'type': 'integer',
        'required': True,
        'default': 1},
    }

def make_default(val):
    def fct(obj, cr, uid):
        return val
    return fct

def _get_returns(self, cr, uid, data, context):

    pool = pooler.get_pool(cr.dbname)
    order_obj=pool.get('pos.order')
    order=order_obj.browse(cr, uid, [data['id']])[0]
    res={}
    fields.clear()
    arch_lst=['<?xml version="1.0"?>', '<form string="%s">' % _('Return lines'), '<label string="%s" colspan="4"/>' % _('Quantities you enter, match to products that will return to the stock.')]
    for m in [line for line in order.lines]:
        quantity=m.qty
        arch_lst.append('<field name="return%s"/>\n<newline/>' % (m.id,))
        fields['return%s' % m.id]={'string':m.product_id.name, 'type':'float', 'required':True, 'default':quantity}
        res.setdefault('returns', []).append(m.id)
    arch_lst.append('</form>')
    arch.string='\n'.join(arch_lst)
    return res

def _create_returns(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    order_obj = pool.get('pos.order')
    lines_obj = pool.get('pos.order.line')
    picking_obj = pool.get('stock.picking')
    stock_move_obj = pool.get('stock.move')
    move_obj = pool.get('stock.move')
    picking_ids = picking_obj.search(cr, uid, [('pos_order', 'in', data['ids']), ('state', '=', 'done')])
    clone_list = []
    date_cur=time.strftime('%Y-%m-%d')
    uom_obj = pool.get('product.uom')
    wf_service = netsvc.LocalService("workflow")
    for order_id in order_obj.browse(cr, uid, data['ids'], context=context):
        prop_ids = pool.get("ir.property").search(cr, uid,[('name', '=', 'property_stock_customer')])
        val = pool.get("ir.property").browse(cr, uid,prop_ids[0]).value
        cr.execute("select s.id from stock_location s, stock_warehouse w where w.lot_stock_id=s.id and w.id= %d "%(order_id.shop_id.warehouse_id.id))
        res=cr.fetchone()
        location_id=res and res[0] or None
        stock_dest_id = int(val.split(',')[1])

        order_obj.write(cr,uid,[order_id.id],{'type_rec':'Exchange'})
        if order_id.invoice_id:
            pool.get('account.invoice').refund(cr, uid, [order_id.invoice_id.id],time.strftime('%Y-%m-%d'), False, order_id.name)
        new_picking=picking_obj.create(cr,uid,{
                                'name':'%s (return)' %order_id.name,
                                'move_lines':[], 'state':'draft',
                                'type':'in',
                                'date':date_cur,   })
        for line in order_id.lines:
            for r in data['form'].get('returns',[]):
                if line.id==r and (data['form']['return%s' %r]!=0.0):
                    new_move=stock_move_obj.create(cr, uid,{
                        'product_qty': data['form']['return%s' %r],
                        'product_uos_qty': uom_obj._compute_qty(cr, uid,data['form']['return%s' %r] ,line.product_id.uom_id.id),
                        'picking_id':new_picking,
                        'product_uom':line.product_id.uom_id.id,
                        'location_id':location_id,
                        'product_id':line.product_id.id,
                        'location_dest_id':stock_dest_id,
                        'name':'%s (return)' %order_id.name,
                        'date':date_cur,
                        'date_planned':date_cur,})
                    lines_obj.write(cr,uid,[line.id],{'qty_rfd':(line.qty or 0.0) + data['form']['return%s' %r],
                                                    'qty':line.qty-(data['form']['return%s' %r] or 0.0)
                    })
        wf_service.trg_validate(uid, 'stock.picking',new_picking,'button_confirm', cr)
        picking_obj.force_assign(cr, uid, [new_picking], context)
    return res

def _create_returns2(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    order_obj = pool.get('pos.order')
    line_obj = pool.get('pos.order.line')
    picking_obj = pool.get('stock.picking')
    stock_move_obj = pool.get('stock.move')
    picking_ids = picking_obj.search(cr, uid, [('pos_order', 'in', data['ids']), ('state', '=', 'done')])
    clone_list = []
    date_cur=time.strftime('%Y-%m-%d')
    uom_obj = pool.get('product.uom')
    wf_service = netsvc.LocalService("workflow")
    for order_id in order_obj.browse(cr, uid, data['ids'], context=context):
        prop_ids = pool.get("ir.property").search(cr, uid,[('name', '=', 'property_stock_customer')])
        val = pool.get("ir.property").browse(cr, uid,prop_ids[0]).value
        cr.execute("select s.id from stock_location s, stock_warehouse w where w.lot_stock_id=s.id and w.id= %d "%(order_id.shop_id.warehouse_id.id))
        res=cr.fetchone()
        location_id=res and res[0] or None
        stock_dest_id = int(val.split(',')[1])

        new_picking=picking_obj.copy(cr, uid, order_id.last_out_picking.id, {'name':'%s (return)' % order_id.name,
                                                                            'move_lines':[], 'state':'draft', 'type':'in',
                                                                            'type':'in',
                                                                            'date':date_cur,   })
        new_order=order_obj.copy(cr,uid,order_id.id, {'name': 'Refund %s'%order_id.name,
                                                      'lines':[],
                                                      'statement_ids':[],
                                                      'last_out_picking':[]})
        for line in order_id.lines:
            for r in data['form'].get('returns',[]):
                if line.id==r and (data['form']['return%s' %r]!=0.0):
                    new_move=stock_move_obj.create(cr, uid,{
                        'product_qty': data['form']['return%s' %r],
                        'product_uos_qty': uom_obj._compute_qty(cr, uid,data['form']['return%s' %r] ,line.product_id.uom_id.id),
                        'picking_id':new_picking,
                        'product_uom':line.product_id.uom_id.id,
                        'location_id':location_id,
                        'product_id':line.product_id.id,
                        'location_dest_id':stock_dest_id,
                        'name':'%s (return)' %order_id.name,
                        'date':date_cur,
                        'date_planned':date_cur,})
                    line_obj.copy(cr,uid,line.id,{'qty':-data['form']['return%s' %r],
                                                'order_id': new_order,
                    })
        order_obj.write(cr,uid, new_order, {'state':'done'})
        wf_service.trg_validate(uid, 'stock.picking',new_picking,'button_confirm', cr)
        picking_obj.force_assign(cr, uid, [new_picking], context)
    act = {
        'domain': "[('id', 'in', ["+str(new_order)+"])]",
        'name': 'Refunded Orders',
        'view_type': 'form',
        'view_mode': 'form,tree',
        'res_model': 'pos.order',
        'auto_refresh':0,
        'res_id':new_order,
        'view_id': False,
        'type': 'ir.actions.act_window'
    }
    return act
def test(self,cr,uid,data,context={}):
  #  import pdb; pdb.set_trace()
    data['id']=data['res_id']
    return {'id':data['res_id']}

#def _raise(self,cr,uid,data,context={}):
#    return datas
#    raise wizard.except_wizard(_('Message'),_('You can not exchange products more than total paid amount.'))


#def _test_exist1(self,cr,uid,data,context={}):
#    return 'choice'

def _test_exist(self,cr,uid,data,context={}):
#    order_obj= pooler.get_pool(cr.dbname).get('pos.order')
#    order_line_obj= pooler.get_pool(cr.dbname).get('pos.order.line')
#    obj=order_obj.browse(cr,uid, data['ids'])[0]
#    am_tot=obj._amount_total(cr, uid, data['ids'])
#    order_obj.write(cr,uid,data['ids'],{'state':'done'})
#    if obj.amount_total == obj.amount_paid:
#        return 'receipt'
#    elif obj.amount_total > obj.amount_paid:
#        sql = """select max(id) from pos_order_line where order_id = %d """%(obj.id)
#        cr.execute(sql)
#        res = cr.fetchone()
#        cr.execute("delete from pos_order_line where id = %d"%(res[0]))
#        cr.commit()
#        return 'choice_raise'
#    else:
    return 'add_p'

def _close(self,cr,uid,data,context={}):
    order_obj= pooler.get_pool(cr.dbname).get('pos.order')
    order_line_obj= pooler.get_pool(cr.dbname).get('pos.order.line')
    obj=order_obj.browse(cr,uid, data['ids'])[0]
    order_obj.write(cr,uid,data['ids'],{'state':'done'})
    if obj.amount_total != obj.amount_paid:
        return 'ask_pay'
    else :
        return 'receipt'




def _add_pdct(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    order_obj = pool.get('pos.order')
    line_obj = pool.get('pos.order.line')
    picking_obj = pool.get('stock.picking')
    wf_service = netsvc.LocalService("workflow")
    prod_obj = pool.get('product.product')
    stock_move_obj = pool.get('stock.move')
    uom_obj = pool.get('product.uom')
    date_cur=time.strftime('%Y-%m-%d')
    order_obj.add_product(cr, uid, data['id'], data['form']['product'],
                            data['form']['quantity'], context=context)
    cr.commit()
    for order_id in order_obj.browse(cr, uid, data['ids'], context=context):
        prod=data['form']['product']
        qty=data['form']['quantity']
        prop_ids = pool.get("ir.property").search(cr, uid,[('name', '=', 'property_stock_customer')])
        val = pool.get("ir.property").browse(cr, uid,prop_ids[0]).value
        cr.execute("select s.id from stock_location s, stock_warehouse w where w.lot_stock_id=s.id and w.id= %d "%(order_id.shop_id.warehouse_id.id))
        res=cr.fetchone()
        location_id=res and res[0] or None
        stock_dest_id = int(val.split(',')[1])

        prod_id=prod_obj.browse(cr,uid,prod)
        new_picking=picking_obj.create(cr,uid,{
                                'name':'%s (Added)' %order_id.name,
                                'move_lines':[],
                                'state':'draft',
                                'type':'out',
                                'date':date_cur,   })
        new_move=stock_move_obj.create(cr, uid,{
                        'product_qty': qty,
                        'product_uos_qty': uom_obj._compute_qty(cr, uid,prod_id.uom_id.id, qty, prod_id.uom_id.id),
                        'picking_id':new_picking,
                        'product_uom':prod_id.uom_id.id,
                        'location_id':location_id,
                        'product_id':prod_id.id,
                        'location_dest_id':stock_dest_id,
                        'name':'%s (return)' %order_id.name,
                        'date':date_cur,
                        'date_planned':date_cur,})

        wf_service.trg_validate(uid, 'stock.picking',new_picking,'button_confirm', cr)
        picking_obj.force_assign(cr, uid, [new_picking], context)
       # order_obj.write(cr,uid,data['id'],{'state':'done','last_out_picking':new_picking})
        order_obj.write(cr,uid,data['id'],{'last_out_picking':new_picking})
    return {}




class wizard_return_picking(wizard.interface):
    states={
        'init':{
            'actions':[_get_returns],
            'result':{'type':'form',
                    'arch':arch,
                    'fields':fields,
                    'state':[('end','Cancel', 'gtk-cancel'),('return','Return goods and Exchange', 'gtk-ok'),('return_w','Return without Refund','gtk-ok')]
                    }
        },
        'return':{
            'actions':[],
            'result':{ 'type': 'action',
                       'action' : _create_returns,
                       'state':'prod'}
        },
        'prod':{
            'actions':[],
            'result': {
                'type': 'form',
                'arch': _form,
                'fields':_fields,
                'state': [('close','Close'),('choice','Continue')]
            }
        },
#        'choice1' : {
#            'actions' : [_add_pdct],
#            'result' : {'type' : 'choice', 'next_state': _test_exist1 }
#        },
        'choice' : {
            'actions' : [],
            'result' : {'type' : 'choice', 'next_state': _test_exist }
        },
#        'choice_raise':{
#                        'actions':[],
#            'result':{ 'type': 'action',
#                       'action' : _raise,
#                       'state':'end'}
#        },
        'add_p' :{
            'actions':[],
            'result':{
            'type':'action',
            'action': _add_pdct,
            'state': 'prod'}
        },
#        'add_pp' :{
#            'actions':[],
#            'result':{
#            'type':'action',
#            'action': _add_pdct,
#            'state': 'end'}
#        },
        'receipt':{
            'result': {
                'type': 'print',
                'report': 'pos.receipt',
                'state': 'end'
            }
        },
        'return_w':{
            'actions':[],
            'result':{'type':'action', 'action':_create_returns2, 'state':'end'}
        },

        'close':{
            'actions' : [],
            'result' : {'type' : 'choice', 'next_state': _close }
        },

       'check': {
            'actions': [],
            'result': {
                'type': 'choice',
                'next_state': _check,
            }
        },

        'ask_pay': {
            'actions': [_pre_init],
            'result': {
                'type': 'form',
                'arch': payment_form,
                'fields': payment_fields,
                'state': (('end', 'Cancel'), ('add_pay', 'Ma_ke payment', 'gtk-ok', True)
                         )
            }
        },
        'add_pay': {
            'actions': [_add_pay],
            'result': {
                'type': 'state',
                'state': "check",
            }
        },


        'invoice': {
            'actions': [create_invoice],
            'result': {
                'type': 'print',
                'report': 'pos.invoice',
                'state': 'end'
            }
        },
        'receipt': {
            'actions': [],
            'result': {
                'type': 'print',
                'report': 'pos.receipt',
                'state': 'end'
            }
        },
        'paid': {
            'actions': [],
            'result': {
                'type': 'state',
                'state': 'end'
            }
        },

    }
wizard_return_picking('pos.return.picking')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
