# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
import datetime
import logging
import time

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
import openerp.tools
from openerp.tools.translate import _
from openerp.exceptions import UserError

from openerp.addons.decimal_precision import decimal_precision as dp

_logger = logging.getLogger(__name__)


class SaleSubscription(osv.osv):
    _name = "sale.subscription"
    _inherits = {'account.analytic.account': 'analytic_account_id'}
    _inherit = ['mail.thread']

    def cron_account_analytic_account(self, cr, uid, context=None):
        context = dict(context or {})
        remind = {}

        def fill_remind(key, domain, write_pending=False):
            base_domain = [
                ('type', '=', 'contract'),
                ('partner_id', '!=', False),
                ('manager_id', '!=', False),
                ('manager_id.email', '!=', False),
            ]
            base_domain.extend(domain)

            accounts_ids = self.search(cr, uid, base_domain, context=context, order='name asc')
            accounts = self.browse(cr, uid, accounts_ids, context=context)
            for account in accounts:
                if write_pending:
                    account.write({'state' : 'pending'})
                remind_user = remind.setdefault(account.manager_id.id, {})
                remind_type = remind_user.setdefault(key, {})
                remind_partner = remind_type.setdefault(account.partner_id, []).append(account)

        # Already expired
        fill_remind("old", [('state', 'in', ['pending'])])

        # Expires now
        fill_remind("new", [('state', 'in', ['draft', 'open']),
                            '&', ('date', '!=', False), ('date', '<=', time.strftime('%Y-%m-%d')),
                            ], True)

        # Expires in less than 30 days
        fill_remind("future", [('state', 'in', ['draft', 'open']), ('date', '!=', False), ('date', '<', (datetime.datetime.now() + datetime.timedelta(30)).strftime("%Y-%m-%d"))])

        context['base_url'] = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        context['action_id'] = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale_contract', 'sale_subscription_action')[1]
        template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale_contract', 'account_analytic_cron_email_template')[1]
        for user_id, data in remind.items():
            context["data"] = data
            _logger.debug("Sending reminder to uid %s", user_id)
            self.pool.get('mail.template').send_mail(cr, uid, template_id, user_id, force_send=True, context=context)

        return True

    def _get_recurring_line_ids(self, cr, uid, ids, context=None):
        result = []
        for line in self.pool.get('sale.subscription.line').browse(cr, uid, ids, context=context):
            result.append(line.analytic_account_id.id)
        return result

    def _get_recurring_price(self, cr, uid, ids, fieldnames, args, context=None):
        result = dict.fromkeys(ids, 0.0)
        for account in self.browse(cr, uid, ids, context=context):
            result[account.id] = sum(line.price_subtotal for line in account.recurring_invoice_line_ids)
        return result

    _columns = {
        'state': fields.selection([('draft', 'New'), ('open', 'In Progress'), ('pending', 'To Renew'),
                                   ('close', 'Closed'), ('cancel', 'Cancelled')],
                                  'Status', required=True, track_visibility='onchange', copy=False),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', required=True, ondelete="cascade", auto_join=True),
        'date_start': fields.date('Start Date'),
        'date': fields.date('End Date', track_visibility='onchange'),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist'),
        'recurring_invoice_line_ids': fields.one2many('sale.subscription.line', 'analytic_account_id', 'Invoice Lines', copy=True),
        'recurring_rule_type': fields.selection([('daily', 'Day(s)'), ('weekly', 'Week(s)'), ('monthly', 'Month(s)'), ('yearly', 'Year(s)'), ], 'Recurrency', help="Invoice automatically repeat at specified interval"),
        'recurring_interval': fields.integer('Repeat Every', help="Repeat every (Days/Week/Month/Year)"),
        'recurring_next_date': fields.date('Date of Next Invoice'),
        'recurring_total': fields.function(_get_recurring_price, string="Recurring Price", type="float", store={
            'account.analytic.account': (lambda s, cr, uid, ids, c={}: ids, ['recurring_invoice_line_ids'], 5),
            'sale.subscription.line': (_get_recurring_line_ids, ['product_id', 'quantity', 'actual_quantity', 'sold_quantity', 'uom_id', 'price_unit', 'discount', 'price_subtotal'], 5),
        }, track_visibility='onchange'),
        'close_reason_id': fields.many2one("sale.subscription.close.reason", "Close Reason", track_visibility='onchange'),
        'type': fields.selection([('contract', 'Contract'), ('template', 'Template')], 'Type'),
        'template_id': fields.many2one('sale.subscription', 'Template of Contract', domain=[('type', '=', 'template')], track_visibility='onchange'),
        'description': fields.text('Description'),
        'user_id': fields.many2one('res.users', 'Responsible', track_visibility='onchange'),
        'manager_id': fields.many2one('res.users', 'Sales Rep', track_visibility='onchange'),
        # Fields that only matters on template
        'plan_description': fields.html(string='Plan Description', help="Describe this contract in a few lines",),
        'user_selectable': fields.boolean(string='Allow Online Order', help="""Leave this unchecked if you don't want this contract template to be available to the customer in the frontend (for a free trial, for example)"""),
    }

    _defaults = {
        'recurring_interval': 1,
        'recurring_next_date': lambda *a: time.strftime('%Y-%m-%d'),
        'recurring_rule_type': 'monthly',
        'user_selectable': True,
        'contract_type': 'regular',
        'state': 'draft',
        'date_start': time.strftime('%Y-%m-%d'),
    }

    def set_open(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'open'}, context=context)

    def set_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def set_pending(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'pending'}, context=context)

    def set_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

    def set_close(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'close'}, context=context)

    def on_change_template(self, cr, uid, ids, template_id, context=None):
        res = {'value': {}}
        if not template_id:
            return res

        template = self.browse(cr, uid, template_id, context=context)
        if template.pricelist_id.id:
            res['value']['pricelist_id'] = template.pricelist_id.id
        if not ids:
            invoice_line_ids = []
            for x in template.recurring_invoice_line_ids:
                invoice_line_ids.append((0, 0, {
                    'product_id': x.product_id.id,
                    'uom_id': x.uom_id.id,
                    'name': x.name,
                    'quantity': x.quantity,
                    'price_unit': x.price_unit,
                    'analytic_account_id': x.analytic_account_id and x.analytic_account_id.id or False,
                }))
            res['value']['recurring_interval'] = template.recurring_interval
            res['value']['recurring_rule_type'] = template.recurring_rule_type
            res['value']['recurring_invoice_line_ids'] = invoice_line_ids
        return res

    def _prepare_invoice_data(self, cr, uid, contract, context=None):
        context = context or {}

        journal_obj = self.pool.get('account.journal')
        fpos_obj = self.pool['account.fiscal.position']
        partner = contract.partner_id

        if not partner:
            raise UserError(_("You must first select a Customer for Contract %s!") % contract.name)

        fpos_id = fpos_obj.get_fiscal_position(cr, uid, partner.company_id.id, partner.id, context=context)
        journal_ids = journal_obj.search(cr, uid, [('type', '=', 'sale'), ('company_id', '=', contract.company_id.id or False)], limit=1)
        if not journal_ids:
            raise UserError(_('Please define a sale journal for the company "%s".') % (contract.company_id.name or '', ))

        partner_payment_term = partner.property_payment_term_id and partner.property_payment_term_id.id or False
        
        next_date = datetime.datetime.strptime(contract.recurring_next_date, "%Y-%m-%d")
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        invoicing_period = relativedelta(**{periods[contract.recurring_rule_type]: contract.recurring_interval})
        new_date = next_date + invoicing_period

        currency_id = False
        if contract.pricelist_id:
            currency_id = contract.pricelist_id.currency_id.id
        elif partner.property_product_pricelist:
            currency_id = partner.property_product_pricelist.currency_id.id
        elif contract.company_id:
            currency_id = contract.company_id.currency_id.id

        invoice = {
            'account_id': partner.property_account_receivable_id.id,
            'type': 'out_invoice',
            'partner_id': partner.id,
            'currency_id': currency_id,
            'journal_id': len(journal_ids) and journal_ids[0] or False,
            'date_invoice': contract.recurring_next_date,
            'origin': contract.code,
            'fiscal_position_id': fpos_id,
            'payment_term_id': partner_payment_term,
            'company_id': contract.company_id.id or False,
            'comment': _("This invoice covers the following period: %s - %s") % (next_date.date(), new_date.date()),
        }
        return invoice

    def _prepare_invoice_line(self, cr, uid, line, fiscal_position, context=None):
        fpos_obj = self.pool.get('account.fiscal.position')
        res = line.product_id
        account_id = res.property_account_income_id.id
        if not account_id:
            account_id = res.categ_id.property_account_income_categ_id.id
        account_id = fpos_obj.map_account(cr, uid, fiscal_position, account_id)

        taxes = res.taxes_id or False
        tax_id = fpos_obj.map_tax(cr, uid, fiscal_position, taxes)
        values = {
            'name': line.name,
            'account_id': account_id,
            'account_analytic_id': line.analytic_account_id.analytic_account_id.id,
            'price_unit': line.price_unit or 0.0,
            'discount': line.discount,
            'quantity': line.quantity,
            'uom_id': line.uom_id.id or False,
            'product_id': line.product_id.id or False,
            'invoice_line_tax_ids': [(6, 0, tax_id)],
        }
        return values

    def _prepare_invoice_lines(self, cr, uid, contract, fiscal_position_id, context=None):
        fpos_obj = self.pool.get('account.fiscal.position')
        fiscal_position = None
        if fiscal_position_id:
            fiscal_position = fpos_obj.browse(cr, uid, fiscal_position_id, context=context)
        invoice_lines = []
        for line in contract.recurring_invoice_line_ids:
            values = self._prepare_invoice_line(cr, uid, line, fiscal_position, context=context)
            invoice_lines.append((0, 0, values))
        return invoice_lines

    def _prepare_invoice(self, cr, uid, contract, context=None):
        invoice = self._prepare_invoice_data(cr, uid, contract, context=context)
        invoice['invoice_line_ids'] = self._prepare_invoice_lines(cr, uid, contract, invoice['fiscal_position_id'], context=context)
        return invoice

    def recurring_invoice(self, cr, uid, ids, context=None):
        return self._recurring_create_invoice(cr, uid, ids, context=context)

    def _cron_recurring_create_invoice(self, cr, uid, context=None):
        return self._recurring_create_invoice(cr, uid, [], automatic=True, context=context)

    def _recurring_create_invoice(self, cr, uid, ids, automatic=False, context=None):
        context = context or {}
        invoice_ids = []
        current_date = time.strftime('%Y-%m-%d')
        if ids:
            contract_ids = ids
        else:
            contract_ids = self.search(cr, uid, [('recurring_next_date', '<=', current_date), ('state', '=', 'open'), ('type', '=', 'contract')])
        if contract_ids:
            cr.execute('SELECT a.company_id, array_agg(sub.id) as ids FROM sale_subscription as sub JOIN account_analytic_account as a ON sub.analytic_account_id = a.id WHERE sub.id IN %s GROUP BY a.company_id', (tuple(contract_ids),))
            for company_id, ids in cr.fetchall():
                for contract in self.browse(cr, uid, ids, context=dict(context, company_id=company_id, force_company=company_id)):
                    try:
                        invoice_values = self._prepare_invoice(cr, uid, contract, context=context)
                        invoice_ids.append(self.pool['account.invoice'].create(cr, uid, invoice_values, context=context))
                        next_date = datetime.datetime.strptime(contract.recurring_next_date or current_date, "%Y-%m-%d")
                        interval = contract.recurring_interval
                        if contract.recurring_rule_type == 'daily':
                            new_date = next_date + relativedelta(days=+interval)
                        elif contract.recurring_rule_type == 'weekly':
                            new_date = next_date + relativedelta(weeks=+interval)
                        elif contract.recurring_rule_type == 'monthly':
                            new_date = next_date + relativedelta(months=+interval)
                        else:
                            new_date = next_date + relativedelta(years=+interval)
                        self.write(cr, uid, [contract.id], {'recurring_next_date': new_date.strftime('%Y-%m-%d')}, context=context)
                        if automatic:
                            cr.commit()
                    except Exception:
                        if automatic:
                            cr.rollback()
                            _logger.exception('Fail to create recurring invoice for contract %s', contract.code)
                        else:
                            raise
        return invoice_ids

    def _prepare_renewal_order_values(self, cr, uid, ids, context=None):
        res = dict()
        for contract in self.browse(cr, uid, ids, context=context):
            order_lines = []
            order_seq_id = self.pool['ir.sequence'].search(cr, uid, [('code', '=', 'sale.order')], context=context)
            order_seq = self.pool['ir.sequence'].browse(cr, uid, order_seq_id, context=context)
            for line in contract.recurring_invoice_line_ids:
                order_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.name_template,
                    'description': line.name,
                    'product_uom': line.uom_id.id,
                    'product_uom_qty': line.quantity,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                }))
            res[contract.id] = {
                'name': order_seq.next_by_id() + ' -  Renewal',
                'pricelist_id': contract.pricelist_id.id,
                'partner_id': contract.partner_id.id,
                'partner_invoice_id': contract.partner_id.id,
                'partner_shipping_id': contract.partner_id.id,
                'currency_id': contract.pricelist_id.currency_id.id,
                'order_line': order_lines,
                'project_id': contract.analytic_account_id.id,
                'update_contract': True,
                'note': contract.description,
                'user_id': contract.manager_id.id,
            }
        return res

    def prepare_renewal_order(self, cr, uid, ids, context=None):
        values = self._prepare_renewal_order_values(cr, uid, ids, context=context)
        for contract in self.browse(cr, uid, ids, context=context):
            order_id = self.pool['sale.order'].create(cr, uid, values[contract.id], context=context)
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": order_id,
        }

    def increment_period(self, cr, uid, ids, context=None):
        for account in self.browse(cr, uid, ids, context=context):
            next_date = datetime.datetime.strptime(account.recurring_next_date, "%Y-%m-%d")
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            invoicing_period = relativedelta(**{periods[account.recurring_rule_type]: account.recurring_interval})
            new_date = next_date + invoicing_period
            self.write(cr, uid, account.id, {'recurring_next_date': new_date}, context=context)

    def action_subscription_invoice(self, cr, uid, ids, context=None):
        analytic_ids = [sub.analytic_account_id.id for sub in self.browse(cr, uid, ids, context=context)]
        invoice_ids = self.pool['account.invoice'].search(cr, uid, [('invoice_line_ids.account_analytic_id', 'in', analytic_ids)], context=context)
        imd = self.pool['ir.model.data']
        list_view_id = imd.xmlid_to_res_id(cr, uid, 'account.invoice_tree')
        form_view_id = imd.xmlid_to_res_id(cr, uid, 'account.invoice_form')
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.invoice",
            "views": [[list_view_id, "tree"], [form_view_id, "form"]],
            "domain": [["id", "in", invoice_ids]],
        }


class SaleSubscriptionLine(osv.osv):
    _name = "sale.subscription.line"

    def _amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.quantity * line.price_unit * (100.0 - line.discount) / 100.0
            if line.analytic_account_id.pricelist_id:
                cur = line.analytic_account_id.pricelist_id.currency_id
                res[line.id] = self.pool.get('res.currency').round(cr, uid, cur, res[line.id])
        return res

    def _compute_quantity(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = max(line.sold_quantity, line.actual_quantity)
        return res

    def _set_quantity(self, cr, uid, ids, name, value, args=None, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, line.id, {'actual_quantity': value}, context=context)

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'analytic_account_id': fields.many2one('sale.subscription', 'Subscription'),
        'name': fields.text('Description', required=True),
        'quantity': fields.function(_compute_quantity, string='Quantity',
                                    store=True,
                                    help="Max between actual and sold quantities; this quantity will be invoiced"),
        'actual_quantity': fields.float('Actual Quantity', help="Quantity actually used by the customer"),
        'sold_quantity': fields.float('Sold Quantity', help="Quantity sold to the customer", required=True),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True),
        'price_unit': fields.float('Unit Price', required=True),
        'discount': fields.float('Discount (%)', digits_compute=dp.get_precision('Discount')),
        'price_subtotal': fields.function(_amount_line, string='Sub Total', type="float", digits_compute=dp.get_precision('Account')),
    }
    _defaults = {
        'sold_quantity': 1,
        'actual_quantity': 0,
    }

    def product_id_change(self, cr, uid, ids, product, uom_id, qty=0, name='', partner_id=False, price_unit=False, pricelist_id=False, company_id=None, context=None):
        context = context or {}
        uom_obj = self.pool.get('product.uom')
        company_id = company_id or False
        local_context = dict(context, company_id=company_id, force_company=company_id, pricelist=pricelist_id)

        if not product:
            return {'value': {'price_unit': 0.0}, 'domain': {'product_uom': []}}
        if partner_id:
            part = self.pool.get('res.partner').browse(cr, uid, partner_id, context=local_context)
            if part.lang:
                local_context.update({'lang': part.lang})

        result = {}
        res = self.pool.get('product.product').browse(cr, uid, product, context=local_context)
        price = False
        if price_unit is not False:
            price = price_unit
        elif pricelist_id:
            price = res.price
        if price is False:
            price = res.list_price
        if not name:
            name = self.pool.get('product.product').name_get(cr, uid, [res.id], context=local_context)[0][1]
            if res.description_sale:
                name += '\n' + res.description_sale

        result.update({'name': name or False, 'uom_id': uom_id or res.uom_id.id or False, 'price_unit': price})

        res_final = {'value': result}
        if result['uom_id'] != res.uom_id.id:
            new_price = uom_obj._compute_price(cr, uid, res.uom_id.id, res_final['value']['price_unit'], result['uom_id'])
            res_final['value']['price_unit'] = new_price

        if not uom_id:
            res_final['domain'] = {'uom_id': [('category_id', '=', res.uom_id.category_id.id)]}
        return res_final

    def product_uom_change(self, cr, uid, ids, product, uom_id, qty=0, name='', partner_id=False, pricelist_id=False, context=None):
        context = context or {}
        if not uom_id:
            return {'value': {'price_unit': 0.0, 'uom_id': uom_id or False}}
        return self.product_id_change(cr, uid, ids, product, uom_id=uom_id, qty=qty, name=name, partner_id=partner_id, pricelist_id=pricelist_id, context=context)


class SaleSubscriptionCloseReason(osv.osv):
    _name = "sale.subscription.close.reason"
    _order = "sequence, id"

    _columns = {
        'name': fields.char('Name', required=True),
        'sequence': fields.integer('Sequence')
    }

    _defaults = {
        'sequence': 10
    }


class res_partner(osv.osv):
        """ Inherits partner and adds contract information in the partner form """
        _inherit = 'res.partner'

        _columns = {
            'contract_ids': fields.one2many('sale.subscription', 'partner_id', 'Subscriptions', readonly=True),
        }
