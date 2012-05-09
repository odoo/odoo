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
import logging
from PIL import Image

import netsvc
from osv import fields, osv
from tools.translate import _
from decimal import Decimal
import decimal_precision as dp

_logger = logging.getLogger(__name__)

class pos_config(osv.osv):
    _name = 'pos.config'

    POS_CONFIG_STATE = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deprecated', 'Deprecated')
    ]

    _columns = {
        'name' : fields.char('Name', size=32,
                             select=1,
                             required=True,
#                             readonly=True,
#                             states={'draft' : [('readonly', False)]}
                            ),
        'journal_ids' : fields.many2many('account.journal', 
                                         'pos_config_journal_rel', 
                                         'pos_config_id', 
                                         'journal_id', 
                                         'Payment Methods',
                                         domain="[('journal_user', '=', True )]",
#                                         readonly=True,
#                                         states={'draft' : [('readonly', False)]}
                                        ),
        'shop_id' : fields.many2one('sale.shop', 'Shop',
                                    required=True,
                                    select=1,
#                                    readonly=True,
#                                    states={'draft' : [('readonly', False)]} 
                                   ),
        'journal_id' : fields.many2one('account.journal', 'Journal',
                                       required=True,
                                       select=1,
                                       domain=[('type', '=', 'sale')],
#                                       readonly=True,
#                                       states={'draft' : [('readonly', False)]}
                                      ),
        'iface_self_checkout' : fields.boolean('Self Checkout Mode'),
        'iface_websql' : fields.boolean('WebSQL (to store data)'),
        'iface_led' : fields.boolean('LED Interface'),
        'iface_cashdrawer' : fields.boolean('Cashdrawer Interface'),
        'iface_payment_terminal' : fields.boolean('Payment Terminal Interface'),
        'iface_electronic_scale' : fields.boolean('Electronic Scale Interface'),
        'iface_barscan' : fields.boolean('BarScan Interface'), 
        'iface_vkeyboard' : fields.boolean('Virtual KeyBoard Interface'),

        'state' : fields.selection(POS_CONFIG_STATE, 'State',
                                   required=True,
                                   readonly=True),

        'sequence_id' : fields.many2one('ir.sequence', 'Sequence',
                                        readonly=True),
        'user_id' : fields.many2one('res.users', 'User',
#                                    readonly=True,
#                                    states={'draft' : [('readonly', False)]}
                                   ),

    }

    _defaults = {
        'state' : 'draft',
        'user_id' : lambda obj, cr, uid, context: uid,
    }

    def _check_only_one_cash_journal(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            has_cash_journal = False

            for journal in record.journal_ids:
                if journal.type == 'cash':
                    if has_cash_journal:
                        return False
                    else:
                        has_cash_journal = True
        return True

    _constraints = [
        (_check_only_one_cash_journal, "You should have only one Cash Journal !", ['journal_id']),
    ]

    def set_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state' : 'draft'}, context=context)

    def set_active(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state' : 'active'}, context=context)

    def set_inactive(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state' : 'inactive'}, context=context)

    def set_deprecate(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state' : 'deprecated'}, context=context)

    def create(self, cr, uid, values, context=None):
        proxy = self.pool.get('ir.sequence.type')

        sequence_values = dict(
            code='pos_%s_sequence' % values['name'].lower(),
            name='POS %s Sequence' % values['name'],
        )

        proxy.create(cr, uid, sequence_values, context=context)

        proxy = self.pool.get('ir.sequence')

        sequence_values = dict(
            code='pos_%s_sequence' % values['name'].lower(),
            name='POS %s Sequence' % values['name'],
            padding=4,
            prefix="%s/%%(year)s/%%(month)s/%%(day)s/"  % values['name'],
        )
        sequence_id = proxy.create(cr, uid, sequence_values, context=context)

        values['sequence_id'] = sequence_id
        return super(pos_config, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.sequence_id and values.get('name', False):
                prefixes = obj.sequence_id.prefix.split('/')
                if len(prefixes) >= 4 and prefixes[0] == obj.name:
                    prefixes[0] = values['name']

                sequence_values = dict(
                    code='pos_%s_sequence' % values['name'].lower(),
                    name='POS %s Sequence' % values['name'],
                    prefix="/".join(prefixes),
                )
                obj.sequence_id.write(sequence_values)

        return super(pos_config, self).write(cr, uid, ids, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.sequence_id:
                obj.sequence_id.unlink()

        return super(pos_config, self).unlink(cr, uid, ids, context=context)

pos_config()

class pos_session(osv.osv):
    _name = 'pos.session'

    POS_SESSION_STATE = [
        ('opening_control', 'Opening Control'),  # Signal open
        ('opened', 'Opened'),                    # Signal closing
        ('closing_control', 'Closing Control'),  # Signal close
        ('closed', 'Closed'),
    ]

    def _compute_cash_register_id(self, cr, uid, ids, fieldnames, args, context=None):
        result = dict.fromkeys(ids, False)
        for record in self.browse(cr, uid, ids, context=context):
            cash_register_id = False
            for bank_statement in record.statement_ids:
                if bank_statement.journal_id.type == 'cash':
                    cash_register_id = bank_statement.id
                    break
            result[record.id] = cash_register_id

        return result

    _columns = {
        'config_id' : fields.many2one('pos.config', 'PoS',
                                      required=True,
                                      select=1,
                                      domain="[('state', '=', 'active')]",
#                                      readonly=True,
#                                      states={'draft' : [('readonly', False)]}
                                     ),

        'name' : fields.char('Session Sequence', size=32,
                             required=True,
                             select=1,
#                             readonly=True,
#                             states={'draft' : [('readonly', False)]}
                            ),
        'user_id' : fields.many2one('res.users', 'User',
                                    required=True,
                                    select=1,
#                                    readonly=True,
#                                    states={'draft' : [('readonly', False)]}
                                   ),
        'start_at' : fields.datetime('Opening Date'), 
        'stop_at' : fields.datetime('Closing Date'),

        'state' : fields.selection(POS_SESSION_STATE, 'State',
                                   required=True,
                                   readonly=True,
                                   select=1),

        'cash_register_id' : fields.function(_compute_cash_register_id, method=True, 
                                             type='many2one', relation='account.bank.statement',
                                             string='Cash Register', store=True),

        'details_ids' : fields.related('cash_register_id', 'details_ids', 
                                       type='one2many', relation='account.cashbox.line',
                                       string='CashBox Lines'),
        'journal_ids' : fields.related('config_id', 'journal_ids',
                                       type='many2many',
                                       readonly=True,
                                       relation='account.journal',
                                       string='Journals'),
        'order_ids' : fields.one2many('pos.order', 'session_id', 'Orders'),

        'statement_ids' : fields.many2many('account.bank.statement', 
                                           'pos_session_statement_rel',
                                           'session_id',
                                           'statement_id',
                                           'Bank Statement',
                                           readonly=True),
    }

    _defaults = {
        'name' : '/',
        'user_id' : lambda obj, cr, uid, context: uid,
        'state' : 'opening_control',
    }

    _sql_constraints = [
        ('uniq_name', 'unique(name)', "The name of this POS Session must be unique !"),
    ]

    def create(self, cr, uid, values, context=None):
        config_id = values.get('config_id', False) or False

        pos_config = None
        if config_id:
            pos_config = self.pool.get('pos.config').browse(cr, uid, config_id, context=context)

            bank_statement_ids = []
            for journal in pos_config.journal_ids:
                bank_values = {
                    'journal_id' : journal.id,
                    'user_id' : pos_config.user_id and pos_config.user_id.id or uid,
                }

                statement_id = self.pool.get('account.bank.statement').create(cr, uid, bank_values, context=context)

                bank_statement_ids.append(statement_id) 

            values.update({
                'name' : pos_config.sequence_id._next(),
                'statement_ids' : [(6, 0, bank_statement_ids)]
            })  

        return super(pos_session, self).create(cr, uid, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            for statement in obj.statement_ids:
                statement.unlink(context=context)
        return True

    def on_change_config(self, cr, uid, ids, config_id, context=None):
        result = dict(value=dict())
        if not config_id:
            result['value']['user_id'] = uid
        else:
            result['value']['user_id'] = self.pool.get('pos.config').browse(cr, uid, config_id, context=context).user_id.id

        return result            

    def wkf_action_open(self, cr, uid, ids, context=None):
        # si pas de date start_at, je balance une date, sinon on utilise celle de l'utilisateur
        for record in self.browse(cr, uid, ids, context=context):
            values = {}
            if not record.start_at:
                values['start_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            values['state'] = 'opened'

            record.write(values, context=context)

            for st in record.statement_ids:
                st.button_open(context=context)

        return True

    def wkf_action_closing_control(self, cr, uid, ids, context=None):
        # Close CashBox
        for record in self.browse(cr, uid, ids, context=context):
            for st in record.statement_ids:
                if st.journal_id.type == 'cash':
                    st.button_confirm_cash(context=context)
                if st.journal_id.type == 'bank':
                    st.button_confirm_bank(context=context)

        return self.write(cr, uid, ids, {'state' : 'closing_control', 'stop_at' : time.strftime('%Y-%m-%d %H:%M:%S')}, context=context)

    def wkf_action_close(self, cr, uid, ids, context=None):
        self._confirm_orders(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'state' : 'closed'}, context=context)

    def _confirm_orders(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")

        for session in self.browse(cr, uid, ids, context=context):
            for order in session.order_ids:
                if order.state != 'paid':
                    raise osv.except_osv(
                        _('Error !'),
                        _("You can not confirm all orders of this session, because they have not the 'paid' status"))
                else:
                    wf_service.trg_validate(uid, 'pos.order', order.id, 'done', cr)

        return True

    def get_current_session(self, cr, uid, context=None):
        current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        domain = [
            ('state', '=', 'open'),
            ('start_at', '>=', time.strftime('%Y-%m-%d 00:00:00')),
            ('user_id', '=', uid),
        ]
        session_ids = self.search(cr, uid, domain, context=context, limit=1, order='start_at desc')
        session_id = session_ids[0] if session_ids else False

        if not session_id:
            pos_config_proxy = self.pool.get('pos.config')
            domain = [
                ('user_id', '=', uid),
                ('state', '=', 'active'),
            ]
            pos_config_ids = pos_config_proxy.search(cr, uid, domain,
                                                     limit=1,
                                                     order='create_date desc',
                                                     context=context)

            if not pos_config_ids:
                raise osv.except_osv(_('Error !'),
                                     _('There is no active PoS Config for this User %s') % current_user.name)

            config = pos_config_proxy.browse(cr, uid, pos_config_ids[0], context=context)

            values = {
                'state' : 'new',
                'start_at' : time.strftime('%Y-%m-%d %H:%M:%S'),
                'config_id' : config.id,
                'journal_id' : config.journal_id.id,
                'user_id': current_user.id,
            }

            session_id = self.create(cr, uid, values, context=context)
            wkf_service = netsvc.LocalService('workflow')
            wkf_service.trg_validate(uid, 'pos.session', session_id, 'opening_control', cr)
            
        return session_id

pos_session()

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

class pos_order(osv.osv):
    _name = "pos.order"
    _description = "Point of Sale"
    _order = "id desc"

    def create_from_ui(self, cr, uid, orders, context=None):
        #_logger.info("orders: %r", orders)
        list = []
        session_id = self.pool.get('pos.session').get_current_session(cr, uid, context=context)
        for order in orders:
            # order :: {'name': 'Order 1329148448062', 'amount_paid': 9.42, 'lines': [[0, 0, {'discount': 0, 'price_unit': 1.46, 'product_id': 124, 'qty': 5}], [0, 0, {'discount': 0, 'price_unit': 0.53, 'product_id': 62, 'qty': 4}]], 'statement_ids': [[0, 0, {'journal_id': 7, 'amount': 9.42, 'name': '2012-02-13 15:54:12', 'account_id': 12, 'statement_id': 21}]], 'amount_tax': 0, 'amount_return': 0, 'amount_total': 9.42}
            order['session_id'] = session_id
            order_obj = self.pool.get('pos.order')
            # get statements out of order because they will be generated with add_payment to ensure
            # the module behavior is the same when using the front-end or the back-end
            if not order['data']['statement_ids']:
                continue
            statement_ids = order['data'].pop('statement_ids')
            order_id = self.create(cr, uid, order, context)
            list.append(order_id)
            # call add_payment; refer to wizard/pos_payment for data structure
            # add_payment launches the 'paid' signal to advance the workflow to the 'paid' state
            data = {
                'journal': statement_ids[0][2]['journal_id'],
                'amount': order['data']['amount_paid'],
                'payment_name': order['data']['name'],
                'payment_date': statement_ids[0][2]['name'],
            }
            order_obj.add_payment(cr, uid, order_id, data, context=context)
        return list

    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state not in ('draft','cancel'):
                raise osv.except_osv(_('Unable to Delete !'), _('In order to delete a sale, it must be new or cancelled.'))
        return super(pos_order, self).unlink(cr, uid, ids, context=context)

    def onchange_partner_id(self, cr, uid, ids, part=False, context=None):
        if not part:
            return {'value': {}}
        pricelist = self.pool.get('res.partner').browse(cr, uid, part, context=context).property_product_pricelist.id
        return {'value': {'pricelist_id': pricelist}}

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
            val1 = val2 = 0.0
            cur = order.pricelist_id.currency_id
            for payment in order.statement_ids:
                res[order.id]['amount_paid'] +=  payment.amount
                res[order.id]['amount_return'] += (payment.amount < 0 and payment.amount or 0)
            for line in order.lines:
                val1 += line.price_subtotal_incl
                val2 += line.price_subtotal
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val1-val2)
            res[order.id]['amount_total'] = cur_obj.round(cr, uid, cur, val1)
        return res

    def _default_sale_journal(self, cr, uid, context=None):
        res = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'sale')], limit=1)
        return res and res[0] or False

    def _default_shop(self, cr, uid, context=None):
        res = self.pool.get('sale.shop').search(cr, uid, [])
        return res and res[0] or False

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        d = {
            'state': 'draft',
            'invoice_id': False,
            'account_move': False,
            'picking_id': False,
            'statement_ids': [],
            'nb_print': 0,
            'name': self.pool.get('ir.sequence').get(cr, uid, 'pos.order'),
        }
        d.update(default)
        return super(pos_order, self).copy(cr, uid, id, d, context=context)

    _columns = {
        'name': fields.char('Order Ref', size=64, required=True, readonly=True),
        'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
        'shop_id': fields.many2one('sale.shop', 'Shop', required=True,
            states={'draft': [('readonly', False)]}, readonly=True),
        'date_order': fields.datetime('Date Ordered', readonly=True, select=True),
        'user_id': fields.many2one('res.users', 'Connected Salesman', help="Person who uses the the cash register. It could be a reliever, a student or an interim employee."),
        'amount_tax': fields.function(_amount_all, string='Taxes', digits_compute=dp.get_precision('Point Of Sale'), multi='all'),
        'amount_total': fields.function(_amount_all, string='Total', multi='all'),
        'amount_paid': fields.function(_amount_all, string='Paid', states={'draft': [('readonly', False)]}, readonly=True, digits_compute=dp.get_precision('Point Of Sale'), multi='all'),
        'amount_return': fields.function(_amount_all, 'Returned', digits_compute=dp.get_precision('Point Of Sale'), multi='all'),
        'lines': fields.one2many('pos.order.line', 'order_id', 'Order Lines', states={'draft': [('readonly', False)]}, readonly=True),
        'statement_ids': fields.one2many('account.bank.statement.line', 'pos_statement_id', 'Payments', states={'draft': [('readonly', False)]}, readonly=True),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', required=True, states={'draft': [('readonly', False)]}, readonly=True),
        'partner_id': fields.many2one('res.partner', 'Customer', change_default=True, select=1, states={'draft': [('readonly', False)], 'paid': [('readonly', False)]}),

        'session_id' : fields.many2one('pos.session', 'Session', 
                                        #required=True,
                                        select=1,
                                        domain="[('state', '=', 'opened')]",
                                        states={'draft' : [('readonly', False)]},
                                        readonly=True),

        'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('paid', 'Paid'),
                                   ('done', 'Posted'),
                                   ('invoiced', 'Invoiced')],
                                  'State', readonly=True),

        'invoice_id': fields.many2one('account.invoice', 'Invoice'),
        'account_move': fields.many2one('account.move', 'Journal Entry', readonly=True),
        'picking_id': fields.many2one('stock.picking', 'Picking', readonly=True),
        'note': fields.text('Internal Notes'),
        'nb_print': fields.integer('Number of Print', readonly=True),
        'sale_journal': fields.many2one('account.journal', 'Journal', required=True, states={'draft': [('readonly', False)]}, readonly=True),
    }

    def _default_pricelist(self, cr, uid, context=None):
        res = self.pool.get('sale.shop').search(cr, uid, [], context=context)
        if res:
            shop = self.pool.get('sale.shop').browse(cr, uid, res[0], context=context)
            return shop.pricelist_id and shop.pricelist_id.id or False
        return False

    _defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'state': 'draft',
        'name': '/', 
        'date_order': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'nb_print': 0,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        'sale_journal': _default_sale_journal,
        'shop_id': _default_shop,
        'pricelist_id': _default_pricelist,
    }

    def create(self, cr, uid, values, context=None):
        values['name'] = self.pool.get('ir.sequence').get(cr, uid, 'pos.order')
        return super(pos_order, self).create(cr, uid, values, context=context)

    def test_paid(self, cr, uid, ids, context=None):
        """A Point of Sale is paid when the sum
        @return: True
        """
        for order in self.browse(cr, uid, ids, context=context):
            if order.lines and not order.amount_total:
                return True
            if (not order.lines) or (not order.statement_ids) or \
                (abs(order.amount_total-order.amount_paid) > 0.00001):
                return False
        return True

    def create_picking(self, cr, uid, ids, context=None):
        """Create a picking for each order and validate it."""
        picking_obj = self.pool.get('stock.picking')
        partner_obj = self.pool.get('res.partner')
        move_obj = self.pool.get('stock.move')

        for order in self.browse(cr, uid, ids, context=context):
            if not order.state=='draft':
                continue
            addr = order.partner_id and partner_obj.address_get(cr, uid, [order.partner_id.id], ['delivery']) or {}
            picking_id = picking_obj.create(cr, uid, {
                'origin': order.name,
                'partner_id': addr.get('delivery',False),
                'type': 'out',
                'company_id': order.company_id.id,
                'move_type': 'direct',
                'note': order.note or "",
                'invoice_state': 'none',
                'auto_picking': True,
            }, context=context)
            self.write(cr, uid, [order.id], {'picking_id': picking_id}, context=context)
            location_id = order.shop_id.warehouse_id.lot_stock_id.id
            output_id = order.shop_id.warehouse_id.lot_output_id.id

            for line in order.lines:
                if line.product_id and line.product_id.type == 'service':
                    continue
                if line.qty < 0:
                    location_id, output_id = output_id, location_id

                move_obj.create(cr, uid, {
                    'name': line.name,
                    'product_uom': line.product_id.uom_id.id,
                    'product_uos': line.product_id.uom_id.id,
                    'picking_id': picking_id,
                    'product_id': line.product_id.id,
                    'product_uos_qty': abs(line.qty),
                    'product_qty': abs(line.qty),
                    'tracking_id': False,
                    'state': 'draft',
                    'location_id': location_id,
                    'location_dest_id': output_id,
                }, context=context)
                if line.qty < 0:
                    location_id, output_id = output_id, location_id

            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
            picking_obj.force_assign(cr, uid, [picking_id], context)
        return True

    def set_to_draft(self, cr, uid, ids, *args):
        if not len(ids):
            return False
        for order in self.browse(cr, uid, ids, context=context):
            if order.state != 'cancel':
                raise osv.except_osv(_('Error!'), _('In order to set to draft a sale, it must be cancelled.'))
        self.write(cr, uid, ids, {'state': 'draft'})
        wf_service = netsvc.LocalService("workflow")
        for i in ids:
            wf_service.trg_create(uid, 'pos.order', i, cr)
        return True

    def cancel_order(self, cr, uid, ids, context=None):
        """ Changes order state to cancel
        @return: True
        """
        stock_picking_obj = self.pool.get('stock.picking')
        for order in self.browse(cr, uid, ids, context=context):
            wf_service.trg_validate(uid, 'stock.picking', order.picking_id.id, 'button_cancel', cr)
            if stock_picking_obj.browse(cr, uid, order.picking_id.id, context=context).state <> 'cancel':
                raise osv.except_osv(_('Error!'), _('Unable to cancel the picking.'))
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True

    def add_payment(self, cr, uid, order_id, data, context=None):
        """Create a new payment for the order"""
        if not context:
            context = {}
        statement_obj = self.pool.get('account.bank.statement')
        statement_line_obj = self.pool.get('account.bank.statement.line')
        prod_obj = self.pool.get('product.product')
        property_obj = self.pool.get('ir.property')
        curr_c = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        curr_company = curr_c.id
        order = self.browse(cr, uid, order_id, context=context)
        ids_new = []
        args = {
            'amount': data['amount'],
        }
        if 'payment_date' in data.keys():
            args['date'] = data['payment_date']
        args['name'] = order.name
        if data.get('payment_name', False):
            args['name'] = args['name'] + ': ' + data['payment_name']
        account_def = property_obj.get(cr, uid, 'property_account_receivable', 'res.partner', context=context)
        args['account_id'] = (order.partner_id and order.partner_id.property_account_receivable \
                             and order.partner_id.property_account_receivable.id) or (account_def and account_def.id) or False
        args['partner_id'] = order.partner_id and order.partner_id.id or None

        if not args['account_id']:
            if not args['partner_id']:
                msg = _('There is no receivable account defined to make payment')
            else:
                msg = _('There is no receivable account defined to make payment for the partner: "%s" (id:%d)') % (order.partner_id.name, order.partner_id.id,)
            raise osv.except_osv(_('Configuration Error !'), msg)

        context.pop('pos_session_id', False)
        domain = [
            ('journal_id', '=', int(data['journal'])),
            ('company_id', '=', curr_company),
            ('user_id', '=', uid),
            ('state', '=', 'open')
        ]
        statement_id = statement_obj.search(cr,uid, domain, context=context)
        if len(statement_id) == 0:
            raise osv.except_osv(_('Error !'), _('You have to open at least one cashbox'))
        if statement_id:
            statement_id = statement_id[0]
        args['statement_id'] = statement_id
        args['pos_statement_id'] = order_id
        args['journal_id'] = int(data['journal'])
        args['type'] = 'customer'
        args['ref'] = order.name
        statement_line_obj.create(cr, uid, args, context=context)
        ids_new.append(statement_id)

        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'pos.order', order_id, 'paid', cr)
        wf_service.trg_write(uid, 'pos.order', order_id, cr)

        return statement_id

    def refund(self, cr, uid, ids, context=None):
        """Create a copy of order  for refund order"""
        clone_list = []
        line_obj = self.pool.get('pos.order.line')
        for order in self.browse(cr, uid, ids, context=context):
            clone_id = self.copy(cr, uid, order.id, {
                'name': order.name + ' REFUND',
            }, context=context)
            clone_list.append(clone_id)

        for clone in self.browse(cr, uid, clone_list, context=context):
            for order_line in clone.lines:
                line_obj.write(cr, uid, [order_line.id], {
                    'qty': -order_line.qty
                }, context=context)

        new_order = ','.join(map(str,clone_list))
        abs = {
            #'domain': "[('id', 'in', ["+new_order+"])]",
            'name': _('Return Products'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id':clone_list[0],
            'view_id': False,
            'context':context,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
        }
        return abs

    def action_invoice_state(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'invoiced'}, context=context)

    def action_invoice(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
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
                'name': order.name,
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
                if line.product_id.description_sale:
                    inv_line['note'] = line.product_id.description_sale
                inv_line['price_unit'] = line.price_unit
                inv_line['discount'] = line.discount
                inv_line['name'] = inv_name
                inv_line['invoice_line_tax_id'] = ('invoice_line_tax_id' in inv_line)\
                    and [(6, 0, inv_line['invoice_line_tax_id'])] or []
                inv_line_ref.create(cr, uid, inv_line, context=context)
            inv_ref.button_reset_taxes(cr, uid, [inv_id], context=context)
            wf_service.trg_validate(uid, 'pos.order', order.id, 'invoice', cr)

        if not inv_ids: return {}

        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        res_id = res and res[1] or False
        return {
            'name': _('Customer Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': inv_ids and inv_ids[0] or False,
        }

    def create_account_move(self, cr, uid, ids, context=None):
        """Create a account move line of order grouped by products or not."""
        account_move_obj = self.pool.get('account.move')
        account_move_line_obj = self.pool.get('account.move.line')
        account_period_obj = self.pool.get('account.period')
        period = account_period_obj.find(cr, uid, context=context)[0]
        account_tax_obj = self.pool.get('account.tax')
        res_obj=self.pool.get('res.users')
        property_obj=self.pool.get('ir.property')

        for order in self.browse(cr, uid, ids, context=context):
            if order.state != 'paid':
                continue

            curr_c = res_obj.browse(cr, uid, uid).company_id
            comp_id = res_obj.browse(cr, order.user_id.id, order.user_id.id).company_id
            comp_id = comp_id and comp_id.id or False
            to_reconcile = []
            group_tax = {}
            account_def = property_obj.get(cr, uid, 'property_account_receivable', 'res.partner', context=context).id

            order_account = order.partner_id and order.partner_id.property_account_receivable and order.partner_id.property_account_receivable.id or account_def or curr_c.account_receivable.id

            # Create an entry for the sale
            move_id = account_move_obj.create(cr, uid, {
                'ref' : order.name,
                'journal_id': order.sale_journal.id,
            }, context=context)

            # Create an move for each order line
            for line in order.lines:
                tax_amount = 0
                taxes = [t for t in line.product_id.taxes_id]
                computed = account_tax_obj.compute_all(cr, uid, taxes, line.price_unit * (100.0-line.discount) / 100.0, line.qty)
                computed_taxes = computed['taxes']

                for tax in computed_taxes:
                    tax_amount += round(tax['amount'], 2)
                    group_key = (tax['tax_code_id'],
                                tax['base_code_id'],
                                tax['account_collected_id'])

                    if group_key in group_tax:
                        group_tax[group_key] += round(tax['amount'], 2)
                    else:
                        group_tax[group_key] = round(tax['amount'], 2)
                amount = line.price_subtotal

                # Search for the income account
                if  line.product_id.property_account_income.id:
                    income_account = line.product_id.property_account_income.id
                elif line.product_id.categ_id.property_account_income_categ.id:
                    income_account = line.product_id.categ_id.property_account_income_categ.id
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
                    'name': line.product_id.name,
                    'date': order.date_order[:10],
                    'ref': order.name,
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
                        'name': "Tax" + line.name +  " (%s)" % (tax.name),
                        'date': order.date_order[:10],
                        'ref': order.name,
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
                    'name': 'Tax',
                    'date': order.date_order[:10],
                    'ref': order.name,
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
                'name': "Trade Receivables", #order.name,
                'date': order.date_order[:10],
                'ref': order.name,
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

            self.write(cr, uid, order.id, {'state':'done', 'account_move': move_id}, context=context)
        return True

    def action_payment(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'payment'}, context=context)

    def action_paid(self, cr, uid, ids, context=None):
        self.create_picking(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'state': 'paid'}, context=context)
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True

    def action_done(self, cr, uid, ids, context=None):
        self.create_account_move(cr, uid, ids, context=context)
        return True

pos_order()

class account_bank_statement(osv.osv):
    _inherit = 'account.bank.statement'
    _columns= {
        'user_id': fields.many2one('res.users', 'User', readonly=True),
    }
    _defaults = {
        'user_id': lambda self,cr,uid,c={}: uid
    }
account_bank_statement()

class account_bank_statement_line(osv.osv):
    _inherit = 'account.bank.statement.line'
    _columns= {
        'pos_statement_id': fields.many2one('pos.order', ondelete='cascade'),
    }
account_bank_statement_line()

class pos_order_line(osv.osv):
    _name = "pos.order.line"
    _description = "Lines of Point of Sale"
    _rec_name = "product_id"

    def _amount_line_all(self, cr, uid, ids, field_names, arg, context=None):
        res = dict([(i, {}) for i in ids])
        account_tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids, context=context):
            taxes = line.product_id.taxes_id
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = account_tax_obj.compute_all(cr, uid, line.product_id.taxes_id, price, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)

            cur = line.order_id.pricelist_id.currency_id
            res[line.id]['price_subtotal'] = cur_obj.round(cr, uid, cur, taxes['total'])
            res[line.id]['price_subtotal_incl'] = cur_obj.round(cr, uid, cur, taxes['total_included'])
        return res

    def onchange_product_id(self, cr, uid, ids, pricelist, product_id, qty=0, partner_id=False, context=None):
       context = context or {}
       if not product_id:
            return {}
       if not pricelist:
           raise osv.except_osv(_('No Pricelist !'),
               _('You have to select a pricelist in the sale form !\n' \
               'Please set one before choosing a product.'))

       price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
               product_id, qty or 1.0, partner_id)[pricelist]

       result = self.onchange_qty(cr, uid, ids, product_id, 0.0, qty, price, context=context)
       result['value']['price_unit'] = price
       return result

    def onchange_qty(self, cr, uid, ids, product, discount, qty, price_unit, context=None):
        result = {}
        if not product:
            return result
        account_tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')

        prod = self.pool.get('product.product').browse(cr, uid, product, context=context)

        taxes = prod.taxes_id
        price = price_unit * (1 - (discount or 0.0) / 100.0)
        taxes = account_tax_obj.compute_all(cr, uid, prod.taxes_id, price, qty, product=prod, partner=False)

        result['price_subtotal'] = taxes['total']
        result['price_subtotal_incl'] = taxes['total_included']
        return {'value': result}

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'name': fields.char('Line No', size=32, required=True),
        'notice': fields.char('Discount Notice', size=128),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True, change_default=True),
        'price_unit': fields.float(string='Unit Price', digits=(16, 2)),
        'qty': fields.float('Quantity', digits=(16, 2)),
        'price_subtotal': fields.function(_amount_line_all, multi='pos_order_line_amount', string='Subtotal w/o Tax', store=True),
        'price_subtotal_incl': fields.function(_amount_line_all, multi='pos_order_line_amount', string='Subtotal', store=True),
        'discount': fields.float('Discount (%)', digits=(16, 2)),
        'order_id': fields.many2one('pos.order', 'Order Ref', ondelete='cascade'),
        'create_date': fields.datetime('Creation Date', readonly=True),
    }

    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'pos.order.line'),
        'qty': lambda *a: 1,
        'discount': lambda *a: 0.0,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }

    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'name': self.pool.get('ir.sequence').get(cr, uid, 'pos.order.line')
        })
        return super(pos_order_line, self).copy_data(cr, uid, id, default, context=context)

pos_order_line()

class pos_category(osv.osv):
    _name = 'pos.category'
    _description = "PoS Category"
    _order = "sequence, name"
    def _check_recursion(self, cr, uid, ids, context=None):
        level = 100
        while len(ids):
            cr.execute('select distinct parent_id from pos_category where id IN %s',(tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive categories.', ['parent_id'])
    ]

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['name','parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'complete_name': fields.function(_name_get_fnc, type="char", string='Name'),
        'parent_id': fields.many2one('pos.category','Parent Category', select=True),
        'child_id': fields.one2many('pos.category', 'parent_id', string='Children Categories'),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of product categories."),
        'to_weight' : fields.boolean('To Weight'),
    }

    _defaults = {
        'to_weight' : False,
    }
pos_category()

import io, StringIO

class product_product(osv.osv):
    _inherit = 'product.product'
    def _get_small_image(self, cr, uid, ids, prop, unknow_none, context=None):
        result = {}
        for obj in self.browse(cr, uid, ids, context=context):
            if not obj.product_image:
                result[obj.id] = False
                continue

            image_stream = io.BytesIO(obj.product_image.decode('base64'))
            img = Image.open(image_stream)
            img.thumbnail((120, 100), Image.ANTIALIAS)
            img_stream = StringIO.StringIO()
            img.save(img_stream, "JPEG")
            result[obj.id] = img_stream.getvalue().encode('base64')
        return result

    _columns = {
        'income_pdt': fields.boolean('PoS Cash Input', help="This is a product you can use to put cash into a statement for the point of sale backend."),
        'expense_pdt': fields.boolean('PoS Cash Output', help="This is a product you can use to take cash from a statement for the point of sale backend, exemple: money lost, transfer to bank, etc."),
        'pos_categ_id': fields.many2one('pos.category','PoS Category',
            help="If you want to sell this product through the point of sale, select the category it belongs to."),
        'product_image_small': fields.function(_get_small_image, string='Small Image', type="binary",
            store = {
                'product.product': (lambda self, cr, uid, ids, c={}: ids, ['product_image'], 10),
            })
    }
product_product()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
