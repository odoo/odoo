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

from osv import osv, fields
import netsvc

class payment_mode(osv.osv):
    _name= 'payment.mode'
    _description= 'Payment Mode'
    _columns = {
        'name': fields.char('Name', size=64, required=True, help='Mode of Payment'),
        'bank_id': fields.many2one('res.partner.bank', "Bank account",
            required=True,help='Bank Account for the Payment Mode'),
        'journal': fields.many2one('account.journal', 'Journal', required=True,
            domain=[('type', 'in', ('bank','cash'))], help='Bank or Cash Journal for the Payment Mode'),
        'company_id': fields.many2one('res.company', 'Company',required=True),
        'partner_id':fields.related('company_id','partner_id',type='many2one',relation='res.partner',string='Partner',store=True,),
        
    }
    _defaults = {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id
    }

    def suitable_bank_types(self, cr, uid, payment_code=None, context=None):
        """Return the codes of the bank type that are suitable
        for the given payment type code"""
        if not payment_code:
            return []
        cr.execute(""" SELECT pb.state
            FROM res_partner_bank pb
            JOIN payment_mode pm ON (pm.bank_id = pb.id)
            WHERE pm.id = %s """, [payment_code])
        return [x[0] for x in cr.fetchall()]
    
    def onchange_company_id (self, cr, uid, ids, company_id=False, context=None):
        result = {}
        if company_id:
            partner_id = self.pool.get('res.company').browse(cr, uid, company_id, context=context).partner_id.id
            result['partner_id'] = partner_id
        return {'value': result}
                

payment_mode()

class payment_order(osv.osv):
    _name = 'payment.order'
    _description = 'Payment Order'
    _rec_name = 'reference'

    def get_wizard(self, type):
        logger = netsvc.Logger()
        logger.notifyChannel("warning", netsvc.LOG_WARNING,
                "No wizard found for the payment type '%s'." % type)
        return None

    def _total(self, cursor, user, ids, name, args, context=None):
        if not ids:
            return {}
        res = {}
        for order in self.browse(cursor, user, ids, context=context):
            if order.line_ids:
                res[order.id] = reduce(lambda x, y: x + y.amount, order.line_ids, 0.0)
            else:
                res[order.id] = 0.0
        return res

    _columns = {
        'date_scheduled': fields.date('Scheduled date if fixed', states={'done':[('readonly', True)]}, help='Select a date if you have chosen Preferred Date to be fixed.'),
        'reference': fields.char('Reference', size=128, required=1, states={'done': [('readonly', True)]}),
        'mode': fields.many2one('payment.mode', 'Payment mode', select=True, required=1, states={'done': [('readonly', True)]}, help='Select the Payment Mode to be applied.'),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('open', 'Confirmed'),
            ('cancel', 'Cancelled'),
            ('done', 'Done')], 'State', select=True,
            help='When an order is placed the state is \'Draft\'.\n Once the bank is confirmed the state is set to \'Confirmed\'.\n Then the order is paid the state is \'Done\'.'),
        'line_ids': fields.one2many('payment.line', 'order_id', 'Payment lines', states={'done': [('readonly', True)]}),
        'total': fields.function(_total, string="Total", method=True, type='float'),
        'user_id': fields.many2one('res.users', 'User', required=True, states={'done': [('readonly', True)]}),
        'date_prefered': fields.selection([
            ('now', 'Directly'),
            ('due', 'Due date'),
            ('fixed', 'Fixed date')
            ], "Preferred date", change_default=True, required=True, states={'done': [('readonly', True)]}, help="Choose an option for the Payment Order:'Fixed' stands for a date specified by you.'Directly' stands for the direct execution.'Due date' stands for the scheduled date of execution."),
        'date_created': fields.date('Creation date', readonly=True),
        'date_done': fields.date('Execution date', readonly=True),
        'company_id': fields.related('mode', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
    }

    _defaults = {
        'user_id': lambda self,cr,uid,context: uid,
        'state': 'draft',
        'date_prefered': 'due',
        'date_created': lambda *a: time.strftime('%Y-%m-%d'),
        'reference': lambda self,cr,uid,context: self.pool.get('ir.sequence').get(cr, uid, 'payment.order'),
    }

    def set_to_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'draft'})
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_create(uid, 'payment.order', id, cr)
        return True

    def action_open(self, cr, uid, ids, *args):
        ir_seq_obj = self.pool.get('ir.sequence')

        for order in self.read(cr, uid, ids, ['reference']):
            if not order['reference']:
                reference = ir_seq_obj.get(cr, uid, 'payment.order')
                self.write(cr, uid, order['id'], {'reference':reference})
        return True

    def set_done(self, cr, uid, ids, *args):
        wf_service = netsvc.LocalService("workflow")
        self.write(cr, uid, ids, {'date_done': time.strftime('%Y-%m-%d')})
        wf_service.trg_validate(uid, 'payment.order', ids[0], 'done', cr)
        return True

    def copy(self, cr, uid, id, default={}, context=None):
        default.update({
            'state': 'draft',
            'line_ids': [],
            'reference': self.pool.get('ir.sequence').get(cr, uid, 'payment.order')
        })
        return super(payment_order, self).copy(cr, uid, id, default, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        payment_line_obj = self.pool.get('payment.line')
        payment_line_ids = []

        if (vals.get('date_prefered', False) == 'fixed' and not vals.get('date_scheduled', False)) or vals.get('date_scheduled', False):
            for order in self.browse(cr, uid, ids, context=context):
                for line in order.line_ids:
                    payment_line_ids.append(line.id)
            payment_line_obj.write(cr, uid, payment_line_ids, {'date': vals.get('date_scheduled', False)}, context=context)
        elif vals.get('date_prefered', False) == 'due':
            vals.update({'date_scheduled': False})
            for order in self.browse(cr, uid, ids, context=context):
                for line in order.line_ids:
                    payment_line_obj.write(cr, uid, [line.id], {'date': line.ml_maturity_date}, context=context)
        elif vals.get('date_prefered', False) == 'now':
            vals.update({'date_scheduled': False})
            for order in self.browse(cr, uid, ids, context=context):
                for line in order.line_ids:
                    payment_line_ids.append(line.id)
            payment_line_obj.write(cr, uid, payment_line_ids, {'date': False}, context=context)
        return super(payment_order, self).write(cr, uid, ids, vals, context=context)

payment_order()

class payment_line(osv.osv):
    _name = 'payment.line'
    _description = 'Payment Line'

    def translate(self, orig):
        return {
                "due_date": "date_maturity",
                "reference": "ref"}.get(orig, orig)

    def info_owner(self, cr, uid, ids, name=None, args=None, context=None):
        if not ids: return {}
        partner_zip_obj = self.pool.get('res.partner.zip')

        result = {}
        info=''
        for line in self.browse(cr, uid, ids, context=context):
            owner = line.order_id.mode.bank_id.partner_id
            result[line.id] = False
            if owner.address:
                for ads in owner.address:
                    if ads.type == 'default':
                        st = ads.street and ads.street or ''
                        st1 = ads.street2 and ads.street2 or ''
                        if 'zip_id' in ads:
                            zip_city = ads.zip_id and partner_zip_obj.name_get(cr, uid, [ads.zip_id.id])[0][1] or ''
                        else:
                            zip = ads.zip and ads.zip or ''
                            city = ads.city and ads.city or  ''
                            zip_city = zip + ' ' + city
                        cntry = ads.country_id and ads.country_id.name or ''
                        info = owner.name + "\n" + st + " " + st1 + "\n" + zip_city + "\n" +cntry
                        result[line.id] = info
                        break
        return result

    def info_partner(self, cr, uid, ids, name=None, args=None, context=None):
        if not ids: return {}
        partner_zip_obj = self.pool.get('res.partner.zip')
        result = {}
        info = ''

        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = False
            if not line.partner_id:
                break
            partner = line.partner_id.name or ''
            if line.partner_id.address:
                for ads in line.partner_id.address:
                    if ads.type == 'default':
                        st = ads.street and ads.street or ''
                        st1 = ads.street2 and ads.street2 or ''
                        if 'zip_id' in ads:
                            zip_city = ads.zip_id and partner_zip_obj.name_get(cr, uid, [ads.zip_id.id])[0][1] or ''
                        else:
                            zip = ads.zip and ads.zip or ''
                            city = ads.city and ads.city or  ''
                            zip_city = zip + ' ' + city
                        cntry = ads.country_id and ads.country_id.name or ''
                        info = partner + "\n" + st + " " + st1 + "\n" + zip_city + "\n" +cntry
                        result[line.id] = info
                        break
        return result

    def select_by_name(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        partner_obj = self.pool.get('res.partner')

        cr.execute("""SELECT pl.id, ml.%s
            FROM account_move_line ml
                INNER JOIN payment_line pl
                ON (ml.id = pl.move_line_id)
                WHERE pl.id IN %%s"""% self.translate(name),
                   (tuple(ids),))
        res = dict(cr.fetchall())

        if name == 'partner_id':
            partner_name = {}
            for p_id, p_name in partner_obj.name_get(cr, uid,
                filter(lambda x:x and x != 0,res.values()), context=context):
                partner_name[p_id] = p_name

            for id in ids:
                if id in res and partner_name:
                    res[id] = (res[id],partner_name[res[id]])
                else:
                    res[id] = (False,False)
        else:
            for id in ids:
                res.setdefault(id, (False, ""))
        return res

    def _amount(self, cursor, user, ids, name, args, context=None):
        if not ids:
            return {}
        currency_obj = self.pool.get('res.currency')
        if context is None:
            context = {}
        res = {}

        for line in self.browse(cursor, user, ids, context=context):
            ctx = context.copy()
            ctx['date'] = line.order_id.date_done or time.strftime('%Y-%m-%d')
            res[line.id] = currency_obj.compute(cursor, user, line.currency.id,
                    line.company_currency.id,
                    line.amount_currency, context=ctx)
        return res

    def _get_currency(self, cr, uid, context=None):
        user_obj = self.pool.get('res.users')
        currency_obj = self.pool.get('res.currency')
        user = user_obj.browse(cr, uid, uid, context=context)

        if user.company_id:
            return user.company_id.currency_id.id
        else:
            return currency_obj.search(cr, uid, [('rate', '=', 1.0)])[0]

    def _get_date(self, cr, uid, context=None):
        if context is None:
            context = {}
        payment_order_obj = self.pool.get('payment.order')
        date = False

        if context.get('order_id') and context['order_id']:
            order = payment_order_obj.browse(cr, uid, context['order_id'], context=context)
            if order.date_prefered == 'fixed':
                date = order.date_scheduled
            else:
                date = time.strftime('%Y-%m-%d')
        return date

    def _get_ml_inv_ref(self, cr, uid, ids, *a):
        res = {}
        for id in self.browse(cr, uid, ids):
            res[id.id] = False
            if id.move_line_id:
                if id.move_line_id.invoice:
                    res[id.id] = id.move_line_id.invoice.id
        return res

    def _get_ml_maturity_date(self, cr, uid, ids, *a):
        res = {}
        for id in self.browse(cr, uid, ids):
            if id.move_line_id:
                res[id.id] = id.move_line_id.date_maturity
            else:
                res[id.id] = False
        return res

    def _get_ml_created_date(self, cr, uid, ids, *a):
        res = {}
        for id in self.browse(cr, uid, ids):
            if id.move_line_id:
                res[id.id] = id.move_line_id.date_created
            else:
                res[id.id] = False
        return res

    _columns = {
        'name': fields.char('Your Reference', size=64, required=True),
        'communication': fields.char('Communication', size=64, required=True, help="Used as the message between ordering customer and current company. Depicts 'What do you want to say to the recipient about this order ?'"),
        'communication2': fields.char('Communication 2', size=64, help='The successor message of Communication.'),
        'move_line_id': fields.many2one('account.move.line', 'Entry line', domain=[('reconcile_id', '=', False), ('account_id.type', '=', 'payable')], help='This Entry Line will be referred for the information of the ordering customer.'),
        'amount_currency': fields.float('Amount in Partner Currency', digits=(16, 2),
            required=True, help='Payment amount in the partner currency'),
        'currency': fields.many2one('res.currency','Partner Currency', required=True),
        'company_currency': fields.many2one('res.currency', 'Company Currency', readonly=True),
        'bank_id': fields.many2one('res.partner.bank', 'Destination Bank Account'),
        'order_id': fields.many2one('payment.order', 'Order', required=True,
            ondelete='cascade', select=True),
        'partner_id': fields.many2one('res.partner', string="Partner", required=True, help='The Ordering Customer'),
        'amount': fields.function(_amount, string='Amount in Company Currency',
            method=True, type='float',
            help='Payment amount in the company currency'),
        'ml_date_created': fields.function(_get_ml_created_date, string="Effective Date",
            method=True, type='date', help="Invoice Effective Date"),
        'ml_maturity_date': fields.function(_get_ml_maturity_date, method=True, type='date', string='Due Date'),
        'ml_inv_ref': fields.function(_get_ml_inv_ref, method=True, type='many2one', relation='account.invoice', string='Invoice Ref.'),
        'info_owner': fields.function(info_owner, string="Owner Account", method=True, type="text", help='Address of the Main Partner'),
        'info_partner': fields.function(info_partner, string="Destination Account", method=True, type="text", help='Address of the Ordering Customer.'),
        'date': fields.date('Payment Date', help="If no payment date is specified, the bank will treat this payment line directly"),
        'create_date': fields.datetime('Created', readonly=True),
        'state': fields.selection([('normal','Free'), ('structured','Structured')], 'Communication Type', required=True),
        'bank_statement_line_id': fields.many2one('account.bank.statement.line', 'Bank statement line'),
        'company_id': fields.related('order_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
    }
    _defaults = {
        'name': lambda obj, cursor, user, context: obj.pool.get('ir.sequence'
            ).get(cursor, user, 'payment.line'),
        'state': 'normal',
        'currency': _get_currency,
        'company_currency': _get_currency,
        'date': _get_date,
    }
    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'The payment line name must be unique!'),
    ]

    def onchange_move_line(self, cr, uid, ids, move_line_id, payment_type, date_prefered, date_scheduled, currency=False, company_currency=False, context=None):
        data = {}
        move_line_obj = self.pool.get('account.move.line')

        data['amount_currency'] = data['communication'] = data['partner_id'] = data['reference'] = data['date_created'] = data['bank_id'] = data['amount'] = False

        if move_line_id:
            line = move_line_obj.browse(cr, uid, move_line_id, context=context)
            data['amount_currency'] = line.amount_to_pay

            res = self.onchange_amount(cr, uid, ids, data['amount_currency'], currency,
                                       company_currency, context)
            if res:
                data['amount'] = res['value']['amount']
            data['partner_id'] = line.partner_id.id
            temp = line.currency_id and line.currency_id.id or False
            if not temp:
                if line.invoice:
                    data['currency'] = line.invoice.currency_id.id
            else:
                data['currency'] = temp

            # calling onchange of partner and updating data dictionary
            temp_dict = self.onchange_partner(cr, uid, ids, line.partner_id.id, payment_type)
            data.update(temp_dict['value'])

            data['reference'] = line.ref
            data['date_created'] = line.date_created
            data['communication'] = line.ref

            if date_prefered == 'now':
                #no payment date => immediate payment
                data['date'] = False
            elif date_prefered == 'due':
                data['date'] = line.date_maturity
            elif date_prefered == 'fixed':
                data['date'] = date_scheduled
        return {'value': data}

    def onchange_amount(self, cr, uid, ids, amount, currency, cmpny_currency, context=None):
        if (not amount) or (not cmpny_currency):
            return {'value': {'amount': False}}
        res = {}
        currency_obj = self.pool.get('res.currency')
        company_amount = currency_obj.compute(cr, uid, currency, cmpny_currency, amount)
        res['amount'] = company_amount
        return {'value': res}

    def onchange_partner(self, cr, uid, ids, partner_id, payment_type, context=None):
        data = {}
        partner_zip_obj = self.pool.get('res.partner.zip')
        partner_obj = self.pool.get('res.partner')
        payment_mode_obj = self.pool.get('payment.mode')
        data['info_partner'] = data['bank_id'] = False

        if partner_id:
            part_obj = partner_obj.browse(cr, uid, partner_id, context=context)
            partner = part_obj.name or ''

            if part_obj.address:
                for ads in part_obj.address:
                    if ads.type == 'default':
                        st = ads.street and ads.street or ''
                        st1 = ads.street2 and ads.street2 or ''

                        if 'zip_id' in ads:
                            zip_city = ads.zip_id and partner_zip_obj.name_get(cr, uid, [ads.zip_id.id])[0][1] or ''
                        else:
                            zip = ads.zip and ads.zip or ''
                            city = ads.city and ads.city or  ''
                            zip_city = zip + ' ' + city

                        cntry = ads.country_id and ads.country_id.name or ''
                        info = partner + "\n" + st + " " + st1 + "\n" + zip_city + "\n" +cntry

                        data['info_partner'] = info

            if part_obj.bank_ids and payment_type:
                bank_type = payment_mode_obj.suitable_bank_types(cr, uid, payment_type, context=context)
                for bank in part_obj.bank_ids:
                    if bank.state in bank_type:
                        data['bank_id'] = bank.id
                        break
        return {'value': data}

    def fields_get(self, cr, uid, fields=None, context=None):
        res = super(payment_line, self).fields_get(cr, uid, fields, context)
        if 'communication2' in res:
            res['communication2'].setdefault('states', {})
            res['communication2']['states']['structured'] = [('readonly', True)]
            res['communication2']['states']['normal'] = [('readonly', False)]
        return res

payment_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
