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
from lxml import etree

from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _

class one2many_mod2(fields.one2many):
    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if context is None:
            context = {}
        res = {}
        for id in ids:
            res[id] = []
        ids2 = None
        if 'journal_id' in context:
            journal = obj.pool.get('account.journal').browse(cr, user, context['journal_id'], context=context)
            pnum = int(name[7]) -1
            plan = journal.plan_id
            if plan and len(plan.plan_ids) > pnum:
                acc_id = plan.plan_ids[pnum].root_analytic_id.id
                ids2 = obj.pool[self._obj].search(cr, user, [(self._fields_id,'in',ids),('analytic_account_id','child_of',[acc_id])], limit=self._limit)
        if ids2 is None:
            ids2 = obj.pool[self._obj].search(cr, user, [(self._fields_id,'in',ids)], limit=self._limit)

        for r in obj.pool[self._obj].read(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
            key = r[self._fields_id]
            if isinstance(key, tuple):
                # Read return a tuple in the case where the field is a many2one
                # but we want to get the id of this field.
                key = key[0]

            res[key].append( r['id'] )
        return res

class account_analytic_line(osv.osv):
    _inherit = 'account.analytic.line'
    _description = 'Analytic Line'

    def _get_amount(self, cr, uid, ids, name, args, context=None):
        res = {}
        for id in ids:
            res.setdefault(id, 0.0)
        for line in self.browse(cr, uid, ids, context=context):
            amount = line.move_id and line.move_id.amount_currency * (line.percentage / 100) or 0.0
            res[line.id] = amount
        return res

    _columns = {
        'amount_currency': fields.function(_get_amount, string="Amount Currency", type="float", store=True, help="The amount expressed in the related account currency if not equal to the company one.", readonly=True),
        'percentage': fields.float('Percentage')
    }


class account_analytic_plan(osv.osv):
    _name = "account.analytic.plan"
    _description = "Analytic Plan"
    _columns = {
        'name': fields.char('Analytic Plan', required=True, select=True),
        'plan_ids': fields.one2many('account.analytic.plan.line', 'plan_id', 'Analytic Plans', copy=True),
    }


class account_analytic_plan_line(osv.osv):
    _name = "account.analytic.plan.line"
    _description = "Analytic Plan Line"
    _order = "sequence, id"
    _columns = {
        'plan_id': fields.many2one('account.analytic.plan','Analytic Plan',required=True),
        'name': fields.char('Axis Name', required=True, select=True),
        'sequence': fields.integer('Sequence'),
        'root_analytic_id': fields.many2one('account.analytic.account', 'Root Account', help="Root account of this plan.", required=False),
        'min_required': fields.float('Minimum Allowed (%)'),
        'max_required': fields.float('Maximum Allowed (%)'),
    }
    _defaults = {
        'min_required': 100.0,
        'max_required': 100.0,
    }


class account_analytic_plan_instance(osv.osv):
    _name = "account.analytic.plan.instance"
    _description = "Analytic Plan Instance"
    _columns = {
        'name': fields.char('Analytic Distribution'),
        'code': fields.char('Distribution Code', size=16),
        'journal_id': fields.many2one('account.analytic.journal', 'Analytic Journal' ),
        'account_ids': fields.one2many('account.analytic.plan.instance.line', 'plan_id', 'Account Id', copy=True),
        'account1_ids': one2many_mod2('account.analytic.plan.instance.line', 'plan_id', 'Account1 Id'),
        'account2_ids': one2many_mod2('account.analytic.plan.instance.line', 'plan_id', 'Account2 Id'),
        'account3_ids': one2many_mod2('account.analytic.plan.instance.line', 'plan_id', 'Account3 Id'),
        'account4_ids': one2many_mod2('account.analytic.plan.instance.line', 'plan_id', 'Account4 Id'),
        'account5_ids': one2many_mod2('account.analytic.plan.instance.line', 'plan_id', 'Account5 Id'),
        'account6_ids': one2many_mod2('account.analytic.plan.instance.line', 'plan_id', 'Account6 Id'),
        'plan_id': fields.many2one('account.analytic.plan', "Model's Plan"),
    }

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        journal_obj = self.pool.get('account.journal')
        if context.get('journal_id', False):
            journal = journal_obj.browse(cr, user, [context['journal_id']], context=context)[0]
            analytic_journal = journal.analytic_journal_id and journal.analytic_journal_id.id or False
            args.append('|')
            args.append(('journal_id', '=', analytic_journal))
            args.append(('journal_id', '=', False))
        res = super(account_analytic_plan_instance, self).search(cr, user, args, offset=offset, limit=limit, order=order,
                                                                 context=context, count=count)
        return res

    def _default_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        journal_obj = self.pool.get('account.journal')
        if context.has_key('journal_id') and context['journal_id']:
            journal = journal_obj.browse(cr, uid, context['journal_id'], context=context)
            if journal.analytic_journal_id:
                return journal.analytic_journal_id.id
        return False

    _defaults = {
        'plan_id': False,
        'journal_id': _default_journal,
    }
    def name_get(self, cr, uid, ids, context=None):
        res = []
        for inst in self.browse(cr, uid, ids, context=context):
            name = inst.name or '/'
            if name and inst.code:
                name=name+' ('+inst.code+')'
            res.append((inst.id, name))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []
        if name:
            ids = self.search(cr, uid, [('code', '=', name)] + args, limit=limit, context=context or {})
            if not ids:
                ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context or {})
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context or {})
        return self.name_get(cr, uid, ids, context or {})

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        wiz_id = self.pool.get('ir.actions.act_window').search(cr, uid, [("name","=","analytic.plan.create.model.action")], context=context)
        res = super(account_analytic_plan_instance,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        journal_obj = self.pool.get('account.journal')
        analytic_plan_obj = self.pool.get('account.analytic.plan')
        if (res['type']=='form'):
            plan_id = False
            if context.get('journal_id', False):
                plan_id = journal_obj.browse(cr, uid, int(context['journal_id']), context=context).plan_id
            elif context.get('plan_id', False):
                plan_id = analytic_plan_obj.browse(cr, uid, int(context['plan_id']), context=context)

            if plan_id:
                i=1
                res['arch'] = """<form string="%s">
    <field name="name"/>
    <field name="code"/>
    <field name="journal_id"/>
    <button name="%d" string="Save This Distribution as a Model" type="action" colspan="2"/>
    """% (tools.to_xml(plan_id.name), wiz_id[0])
                for line in plan_id.plan_ids:
                    res['arch']+="""
                    <field name="account%d_ids" string="%s" nolabel="1" colspan="4">
                    <tree string="%s" editable="bottom">
                        <field name="rate"/>
                        <field name="analytic_account_id" domain="[('parent_id','child_of',[%d])]" groups="analytic.group_analytic_accounting"/>
                    </tree>
                </field>
                <newline/>"""%(i,tools.to_xml(line.name),tools.to_xml(line.name),line.root_analytic_id and line.root_analytic_id.id or 0)
                    i+=1
                res['arch'] += "</form>"
                doc = etree.fromstring(res['arch'].encode('utf8'))
                xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
                res['arch'] = xarch
                res['fields'] = xfields
            return res
        else:
            return res

    def create(self, cr, uid, vals, context=None):
        journal_obj = self.pool.get('account.journal')
        ana_plan_instance_obj = self.pool.get('account.analytic.plan.instance')
        acct_anal_acct = self.pool.get('account.analytic.account')
        acct_anal_plan_line_obj = self.pool.get('account.analytic.plan.line')
        if context and context.get('journal_id'):
            journal = journal_obj.browse(cr, uid, context['journal_id'], context=context)

            pids = ana_plan_instance_obj.search(cr, uid, [('name','=',vals['name']), ('code','=',vals['code']), ('plan_id','<>',False)], context=context)
            if pids:
                raise osv.except_osv(_('Error!'), _('A model with this name and code already exists.'))

            res = acct_anal_plan_line_obj.search(cr, uid, [('plan_id','=',journal.plan_id.id)], context=context)
            for i in res:
                total_per_plan = 0
                item = acct_anal_plan_line_obj.browse(cr, uid, i, context=context)
                temp_list = ['account1_ids','account2_ids','account3_ids','account4_ids','account5_ids','account6_ids']
                for l in temp_list:
                    if vals.has_key(l):
                        for tempo in vals[l]:
                            if acct_anal_acct.search(cr, uid, [('parent_id', 'child_of', [item.root_analytic_id.id]), ('id', '=', tempo[2]['analytic_account_id'])], context=context):
                                total_per_plan += tempo[2]['rate']
                if total_per_plan < item.min_required or total_per_plan > item.max_required:
                    raise osv.except_osv(_('Error!'),_('The total should be between %s and %s.') % (str(item.min_required), str(item.max_required)))

        return super(account_analytic_plan_instance, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        if context is None:
            context = {}
        this = self.browse(cr, uid, ids[0], context=context)
        invoice_line_obj = self.pool.get('account.invoice.line')
        if this.plan_id and not vals.has_key('plan_id'):
            #this instance is a model, so we have to create a new plan instance instead of modifying it
            #copy the existing model
            temp_id = self.copy(cr, uid, this.id, None, context=context)
            #get the list of the invoice line that were linked to the model
            lists = invoice_line_obj.search(cr, uid, [('analytics_id','=',this.id)], context=context)
            #make them link to the copy
            invoice_line_obj.write(cr, uid, lists, {'analytics_id':temp_id}, context=context)

            #and finally modify the old model to be not a model anymore
            vals['plan_id'] = False
            if not vals.has_key('name'):
                vals['name'] = this.name and (str(this.name)+'*') or "*"
            if not vals.has_key('code'):
                vals['code'] = this.code and (str(this.code)+'*') or "*"
        return super(account_analytic_plan_instance, self).write(cr, uid, ids, vals, context=context)


class account_analytic_plan_instance_line(osv.osv):
    _name = "account.analytic.plan.instance.line"
    _description = "Analytic Instance Line"
    _rec_name = "analytic_account_id"
    _columns = {
        'plan_id': fields.many2one('account.analytic.plan.instance', 'Plan Id'),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', required=True, domain=[('type','<>','view')]),
        'rate': fields.float('Rate (%)', required=True),
    }
    _defaults = {
        'rate': 100.0
    }
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['analytic_account_id'], context=context)
        res = []
        for record in reads:
            res.append((record['id'], record['analytic_account_id']))
        return res


class account_journal(osv.osv):
    _inherit = "account.journal"
    _name = "account.journal"
    _columns = {
        'plan_id': fields.many2one('account.analytic.plan', 'Analytic Plans'),
    }


class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"
    _name = "account.invoice.line"
    _columns = {
        'analytics_id': fields.many2one('account.analytic.plan.instance', 'Analytic Distribution'),
    }

    def create(self, cr, uid, vals, context=None):
        if 'analytics_id' in vals and isinstance(vals['analytics_id'], tuple):
            vals['analytics_id'] = vals['analytics_id'][0]
        return super(account_invoice_line, self).create(cr, uid, vals, context=context)

    def move_line_get_item(self, cr, uid, line, context=None):
        res = super(account_invoice_line, self).move_line_get_item(cr, uid, line, context=context)
        res ['analytics_id'] = line.analytics_id and line.analytics_id.id or False
        return res

    def product_id_change(self, cr, uid, ids, product, uom_id, qty=0, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, currency_id=False, company_id=None, context=None):
        res_prod = super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom_id, qty, name, type, partner_id, fposition_id, price_unit, currency_id, company_id=company_id, context=context)
        rec = self.pool.get('account.analytic.default').account_get(cr, uid, product, partner_id, uid, time.strftime('%Y-%m-%d'), context=context)
        if rec and rec.analytics_id:
            res_prod['value'].update({'analytics_id': rec.analytics_id.id})
        return res_prod


class account_move_line(osv.osv):

    _inherit = "account.move.line"
    _name = "account.move.line"
    _columns = {
        'analytics_id':fields.many2one('account.analytic.plan.instance', 'Analytic Distribution'),
    }

    def _default_get_move_form_hook(self, cursor, user, data):
        data = super(account_move_line, self)._default_get_move_form_hook(cursor, user, data)
        if data.has_key('analytics_id'):
            del(data['analytics_id'])
        return data

    def create_analytic_lines(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        super(account_move_line, self).create_analytic_lines(cr, uid, ids, context=context)
        analytic_line_obj = self.pool.get('account.analytic.line')
        for line in self.browse(cr, uid, ids, context=context):
           if line.analytics_id:
               if not line.journal_id.analytic_journal_id:
                   raise osv.except_osv(_('No Analytic Journal!'),_("You have to define an analytic journal on the '%s' journal.") % (line.journal_id.name,))

               toremove = analytic_line_obj.search(cr, uid, [('move_id','=',line.id)], context=context)
               if toremove:
                    analytic_line_obj.unlink(cr, uid, toremove, context=context)
               for line2 in line.analytics_id.account_ids:
                   val = (line.credit or  0.0) - (line.debit or 0.0)
                   amt=val * (line2.rate/100)
                   al_vals={
                       'name': line.name,
                       'date': line.date,
                       'account_id': line2.analytic_account_id.id,
                       'unit_amount': line.quantity,
                       'product_id': line.product_id and line.product_id.id or False,
                       'product_uom_id': line.product_uom_id and line.product_uom_id.id or False,
                       'amount': amt,
                       'general_account_id': line.account_id.id,
                       'move_id': line.id,
                       'journal_id': line.journal_id.analytic_journal_id.id,
                       'ref': line.ref,
                       'percentage': line2.rate
                   }
                   analytic_line_obj.create(cr, uid, al_vals, context=context)
        return True

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        result = super(account_move_line, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        return result


class account_invoice(osv.osv):
    _name = "account.invoice"
    _inherit = "account.invoice"

    def line_get_convert(self, cr, uid, x, part, date, context=None):
        res=super(account_invoice,self).line_get_convert(cr, uid, x, part, date, context=context)
        res['analytics_id'] = x.get('analytics_id', False)
        return res

    def _get_analytic_lines(self, cr, uid, ids, context=None):
        inv = self.browse(cr, uid, ids)[0]
        cur_obj = self.pool.get('res.currency')
        invoice_line_obj = self.pool.get('account.invoice.line')
        acct_ins_obj = self.pool.get('account.analytic.plan.instance')
        company_currency = inv.company_id.currency_id.id
        if inv.type in ('out_invoice', 'in_refund'):
            sign = 1
        else:
            sign = -1

        iml = invoice_line_obj.move_line_get(cr, uid, inv.id, context=context)

        for il in iml:
            if il.get('analytics_id', False):

                if inv.type in ('in_invoice', 'in_refund'):
                    ref = inv.reference
                else:
                    ref = inv.number
                obj_move_line = acct_ins_obj.browse(cr, uid, il['analytics_id'], context=context)
                ctx = context.copy()
                ctx.update({'date': inv.date_invoice})
                amount_calc = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, il['price'], context=ctx) * sign
                qty = il['quantity']
                il['analytic_lines'] = []
                for line2 in obj_move_line.account_ids:
                    amt = amount_calc * (line2.rate/100)
                    qtty = qty* (line2.rate/100)
                    al_vals = {
                        'name': il['name'],
                        'date': inv['date_invoice'],
                        'unit_amount': qtty,
                        'product_id': il['product_id'],
                        'account_id': line2.analytic_account_id.id,
                        'amount': amt,
                        'product_uom_id': il['uos_id'],
                        'general_account_id': il['account_id'],
                        'journal_id': self._get_journal_analytic(cr, uid, inv.type),
                        'ref': ref,
                    }
                    il['analytic_lines'].append((0, 0, al_vals))
        return iml


class account_analytic_plan(osv.osv):
    _inherit = "account.analytic.plan"
    _columns = {
        'default_instance_id': fields.many2one('account.analytic.plan.instance', 'Default Entries'),
    }

class analytic_default(osv.osv):
    _inherit = "account.analytic.default"
    _columns = {
        'analytics_id': fields.many2one('account.analytic.plan.instance', 'Analytic Distribution'),
    }


class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    # Method overridden to set the analytic account by default on criterion match
    def invoice_line_create(self, cr, uid, ids, context=None):
        create_ids = super(sale_order_line,self).invoice_line_create(cr, uid, ids, context=context)
        inv_line_obj = self.pool.get('account.invoice.line')
        acct_anal_def_obj = self.pool.get('account.analytic.default')
        if ids:
            sale_line = self.browse(cr, uid, ids[0], context=context)
            for line in inv_line_obj.browse(cr, uid, create_ids, context=context):
                rec = acct_anal_def_obj.account_get(cr, uid, line.product_id.id,
                        sale_line.order_id.partner_id.id, uid, time.strftime('%Y-%m-%d'),
                        sale_line.order_id.company_id.id, context=context)

                if rec:
                    inv_line_obj.write(cr, uid, [line.id], {'analytics_id': rec.analytics_id.id}, context=context)
        return create_ids



class account_bank_statement(osv.osv):
    _inherit = "account.bank.statement"
    _name = "account.bank.statement"

    def _prepare_bank_move_line(self, cr, uid, st_line, move_id, amount, company_currency_id, context=None):
        result = super(account_bank_statement,self)._prepare_bank_move_line(cr, uid, st_line, 
            move_id, amount, company_currency_id, context=context)
        result['analytics_id'] = st_line.analytics_id.id
        return result

    def button_confirm_bank(self, cr, uid, ids, context=None):
        super(account_bank_statement,self).button_confirm_bank(cr, uid, ids, context=context)
        for st in self.browse(cr, uid, ids, context=context):
            for st_line in st.line_ids:
                if st_line.analytics_id:
                    if not st.journal_id.analytic_journal_id:
                        raise osv.except_osv(_('No Analytic Journal!'),_("You have to define an analytic journal on the '%s' journal.") % (st.journal_id.name,))
                if not st_line.amount:
                    continue
        return True



class account_bank_statement_line(osv.osv):
    _inherit = "account.bank.statement.line"
    _name = "account.bank.statement.line"
    _columns = {
        'analytics_id': fields.many2one('account.analytic.plan.instance', 'Analytic Distribution'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
