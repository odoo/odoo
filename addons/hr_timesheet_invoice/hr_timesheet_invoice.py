# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

class hr_timesheet_invoice_factor(osv.osv):
    _name = "hr_timesheet_invoice.factor"
    _description = "Invoice Rate"
    _order = 'factor'
    _columns = {
        'name': fields.char('Internal Name', required=True, translate=True),
        'customer_name': fields.char('Name', help="Label for the customer"),
        'factor': fields.float('Discount (%)', required=True, help="Discount in percentage"),
    }
    _defaults = {
        'factor': lambda *a: 0.0,
    }


class account_analytic_account(osv.osv):
    _inherit = "account.analytic.account"
    _columns = {
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist',
            help="The product to invoice is defined on the employee form, the price will be deducted by this pricelist on the product."),
        'amount_max': fields.float('Max. Invoice Price',
            help="Keep empty if this contract is not limited to a total fixed price."),
        'to_invoice': fields.many2one('hr_timesheet_invoice.factor', 'Timesheet Invoicing Ratio',
            help="You usually invoice 100% of the timesheets. But if you mix fixed price and timesheet invoicing, you may use another ratio. For instance, if you do a 20% advance invoice (fixed price, based on a sales order), you should invoice the rest on timesheet with a 80% ratio."),
    }

    _defaults = {
         'pricelist_id': lambda self, cr, uid, c: self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'product.list0'),
         'to_invoice': lambda self, cr, uid, c: self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'hr_timesheet_invoice.timesheet_invoice_factor1')
    }

    def on_change_partner_id(self, cr, uid, ids, partner_id, name, context=None):
        res = super(account_analytic_account, self).on_change_partner_id(cr, uid, ids, partner_id, name, context=context)
        if partner_id:
            part = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
            if pricelist:
                res['value']['pricelist_id'] = pricelist
        return res

    def set_close(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'close'}, context=context)

    def set_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'cancelled'}, context=context)

    def set_open(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'open'}, context=context)

    def set_pending(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'pending'}, context=context)


class account_analytic_line(osv.osv):
    _inherit = 'account.analytic.line'
    _columns = {
        'invoice_id': fields.many2one('account.invoice', 'Invoice', ondelete="set null", copy=False),
        'to_invoice': fields.many2one('hr_timesheet_invoice.factor', 'Invoiceable', help="It allows to set the discount while making invoice, keep empty if the activities should not be invoiced."),
    }

    def _default_general_account(self, cr, uid, context=None):
        proxy = self.pool.get('hr.employee')
        record_ids = proxy.search(cr, uid, [('user_id', '=', uid)], context=context)
        if record_ids:
            employee = proxy.browse(cr, uid, record_ids[0], context=context)
            if employee.product_id and employee.product_id.property_account_income_id:
                return employee.product_id.property_account_income_id.id
        return False

    _defaults = {
        'general_account_id': _default_general_account,
    }

    def write(self, cr, uid, ids, vals, context=None):
        self._check_inv(cr, uid, ids, vals)
        return super(account_analytic_line, self).write(cr, uid, ids, vals,
                context=context)

    def unlink(self, cr, uid, ids, context=None):
        if any(line.invoice_id.id for line in self.browse(cr, uid, ids, context)):
            raise UserError(_('You cannot delete an invoiced analytic line!'))
        return super(account_analytic_line, self).unlink(cr, uid, ids, context)

    def _check_inv(self, cr, uid, ids, vals, context=None):
        select = ids
        if isinstance(select, (int, long)):
            select = [ids]
        if (not vals.has_key('invoice_id')) or vals['invoice_id'] == False:
            for line in self.browse(cr, uid, select, context):
                if line.invoice_id:
                    raise UserError(_('You cannot modify an invoiced analytic line!'))
        return True

    def _get_invoice_price(self, cr, uid, account, product_id, user_id, qty, context={}):
        pro_price_obj = self.pool.get('product.pricelist')
        if account.pricelist_id:
            pl = account.pricelist_id.id
            price = pro_price_obj.price_get(cr, uid, [pl], product_id, qty or 1.0, account.partner_id.id, context=context)[pl]
        else:
            price = 0.0
        return price

    def _prepare_cost_invoice(self, cr, uid, partner, company_id, currency_id, analytic_line_ids, group_by_partner=False, context=None):
        """ returns values used to create main invoice from analytic lines"""
        account_payment_term_obj = self.pool['account.payment.term']
        if group_by_partner:
            invoice_name = partner.name
        else:
            invoice_name = analytic_line_ids[0].account_id.name
        date_due = False
        if partner.property_payment_term_id:
            pterm_list = account_payment_term_obj.compute(cr, uid,
                    partner.property_payment_term_id.id, value=1,
                    date_ref=time.strftime('%Y-%m-%d'))
            if pterm_list:
                pterm_list = [line[0] for line in pterm_list]
                pterm_list.sort()
                date_due = pterm_list[-1][0]
        return {
            'name': "%s - %s" % (time.strftime('%d/%m/%Y'), invoice_name),
            'partner_id': partner.id,
            'company_id': company_id,
            'payment_term_id': partner.property_payment_term_id.id or False,
            'account_id': partner.property_account_receivable_id.id,
            'currency_id': currency_id,
            'date_due': date_due,
            'fiscal_position_id': partner.property_account_position_id.id
        }

    def _prepare_cost_invoice_line(self, cr, uid, invoice_id, product_id, uom, user_id,
                factor_id, account, analytic_line_ids, journal_type, data, context=None):
        product_obj = self.pool['product.product']

        uom_context = dict(context or {}, uom=uom)

        total_price = sum(l.amount for l in analytic_line_ids)
        total_qty = sum(l.unit_amount for l in analytic_line_ids)

        if data.get('product'):
            # force product, use its public price
            if isinstance(data['product'], (tuple, list)):
                product_id = data['product'][0]
            else:
                product_id = data['product']
            unit_price = self._get_invoice_price(cr, uid, account, product_id, user_id, total_qty, uom_context)
        elif journal_type == 'general' and product_id:
            # timesheets, use sale price
            unit_price = self._get_invoice_price(cr, uid, account, product_id, user_id, total_qty, uom_context)
        else:
            # expenses, using price from amount field
            unit_price = total_price*-1.0 / total_qty

        factor = self.pool['hr_timesheet_invoice.factor'].browse(cr, uid, factor_id, context=uom_context)
        factor_name = factor.customer_name or ''
        curr_invoice_line = {
            'price_unit': unit_price,
            'quantity': total_qty,
            'product_id': product_id,
            'discount': factor.factor,
            'invoice_id': invoice_id,
            'name': factor_name,
            'uos_id': uom,
            'account_analytic_id': account.id,
        }

        if product_id:
            product = product_obj.browse(cr, uid, product_id, context=uom_context)
            factor_name = product_obj.name_get(cr, uid, [product_id], context=uom_context)[0][1]
            if factor.customer_name:
                factor_name += ' - ' + factor.customer_name

            general_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
            if not general_account:
                raise UserError(_("Configuration Error!") + '\n' + _("Please define income account for product '%s'.") % product.name)
            taxes = product.taxes_id or general_account.tax_ids
            tax = self.pool['account.fiscal.position'].map_tax(cr, uid, account.partner_id.property_account_position_id, taxes)
            curr_invoice_line.update({
                'invoice_line_tax_ids': [(6, 0, tax)],
                'name': factor_name,
                'account_id': general_account.id,
            })

            note = []
            for line in analytic_line_ids:
                # set invoice_line_note
                details = []
                if data.get('date', False):
                    details.append(line['date'])
                if data.get('time', False):
                    if line['product_uom_id']:
                        details.append("%s %s" % (line.unit_amount, line.product_uom_id.name))
                    else:
                        details.append("%s" % (line['unit_amount'], ))
                if data.get('name', False):
                    details.append(line['name'])
                if details:
                    note.append(u' - '.join(map(lambda x: unicode(x) or '', details)))
            if note:
                curr_invoice_line['name'] += "\n" + ("\n".join(map(lambda x: unicode(x) or '', note)))
        return curr_invoice_line

    def invoice_cost_create(self, cr, uid, ids, data=None, context=None):
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        analytic_line_obj = self.pool.get('account.analytic.line')
        invoices = []
        if context is None:
            context = {}
        if data is None:
            data = {}

        # use key (partner/account, company, currency)
        # creates one invoice per key
        invoice_grouping = {}
        # grouping on partner instead of analytic account
        group_by_partner = data.get('group_by_partner', False)

        currency_id = False
        # prepare for iteration on journal and accounts
        for line in self.browse(cr, uid, ids, context=context):
            # check if currency is the same in different accounts when grouping by partner
            if not currency_id :

                currency_id = line.account_id.pricelist_id.currency_id.id
            if line.account_id.pricelist_id and line.account_id.pricelist_id.currency_id:
                if line.account_id.pricelist_id.currency_id.id != currency_id and group_by_partner:
                    raise UserError(_('You cannot group invoices having different currencies on different analytic accounts for the same partner.'))

            if group_by_partner:
                key = (line.account_id.partner_id.id,
                    line.account_id.company_id.id,
                    line.account_id.pricelist_id.currency_id.id)
                invoice_grouping.setdefault(key, []).append(line)
            else:
                key = (line.account_id.id,
                    line.account_id.company_id.id,
                    line.account_id.pricelist_id.currency_id.id)
                invoice_grouping.setdefault(key, []).append(line)

        for (key_id, company_id, currency_id), analytic_line_ids in invoice_grouping.items():
            # key_id is either an account.analytic.account, either a res.partner
            # don't really care, what's important is the analytic lines that
            # will be used to create the invoice lines

            partner = analytic_line_ids[0].account_id.partner_id  # will be the same for every line

            curr_invoice = self._prepare_cost_invoice(cr, uid, partner, company_id, currency_id, analytic_line_ids, group_by_partner, context=context)
            invoice_context = dict(context,
                    lang=partner.lang,
                    force_company=company_id,  # set force_company in context so the correct product properties are selected (eg. income account)
                    company_id=company_id)  # set company_id in context, so the correct default journal will be selected
            last_invoice = invoice_obj.create(cr, uid, curr_invoice, context=invoice_context)
            invoices.append(last_invoice)

            # use key (product, uom, user, invoiceable, analytic account, journal type)
            # creates one invoice line per key
            invoice_lines_grouping = {}
            for analytic_line in analytic_line_ids:
                account = analytic_line.account_id
                if (not partner) or not (account.pricelist_id):
                    raise UserError(_('Contract incomplete. Please fill in the Customer and Pricelist fields for %s.') % (account.name))

                if not analytic_line.to_invoice:
                    raise UserError(_('Trying to invoice non invoiceable line for %s.') % (analytic_line.product_id.name))

                if not analytic_line.product_id and not data['product']:
                    raise UserError(_('No product associated with %s, force a product.') % (analytic_line.name))

                key = (analytic_line.product_id.id,
                    analytic_line.product_uom_id.id,
                    analytic_line.user_id.id,
                    analytic_line.to_invoice.id,
                    analytic_line.account_id,
                    analytic_line.journal_id.type)
                # We want to retrieve the data in the partner language for the invoice creation
                analytic_line = analytic_line_obj.browse(cr, uid , [line.id for line in analytic_line], context=invoice_context)
                invoice_lines_grouping.setdefault(key, []).append(analytic_line)

            # finally creates the invoice line
            for (product_id, uom, user_id, factor_id, account, journal_type), lines_to_invoice in invoice_lines_grouping.items():
                curr_invoice_line = self._prepare_cost_invoice_line(cr, uid, last_invoice,
                    product_id, uom, user_id, factor_id, account, lines_to_invoice,
                    journal_type, data, context=invoice_context)

                invoice_line_obj.create(cr, uid, curr_invoice_line, context=context)
            self.write(cr, uid, [l.id for l in analytic_line_ids], {'invoice_id': last_invoice}, context=context)
            invoice_obj.compute_taxes(cr, uid, [last_invoice], context)
        return invoices

    def on_change_account_id(self, cr, uid, ids, account_id, user_id=False, unit_amount=0, is_timesheet=False, context=None):
        res = {'value': {}}
        if is_timesheet and account_id:
            acc = self.pool.get('account.analytic.account').browse(cr, uid, account_id, context=context)
            st = acc.to_invoice.id
            res['value']['to_invoice'] = st or False
            if acc.state == 'pending':
                res['warning'] = {
                    'title': _('Warning'),
                    'message': _('The analytic account is in pending state.\nYou should not work on this account !')
                }
            elif acc.state == 'close' or acc.state == 'cancelled':
                raise osv.except_osv(_('Invalid Analytic Account!'), _('You cannot select a Analytic Account which is in Close or Cancelled state.'))
        return res


class account_invoice(osv.osv):
    _inherit = "account.invoice"

    def _get_analytic_lines(self, cr, uid, ids, context=None):
        iml = super(account_invoice, self)._get_analytic_lines(cr, uid, ids, context=context)

        inv = self.browse(cr, uid, ids, context=context)[0]
        if inv.type == 'in_invoice':
            obj_analytic_account = self.pool.get('account.analytic.account')
            for il in iml:
                if il['account_analytic_id']:
                    # *-* browse (or refactor to avoid read inside the loop)
                    to_invoice = obj_analytic_account.read(cr, uid, [il['account_analytic_id']], ['to_invoice'], context=context)[0]['to_invoice']
                    if to_invoice:
                        il['analytic_line_ids'][0][2]['to_invoice'] = to_invoice[0]
        return iml


class account_move_line(osv.osv):
    _inherit = "account.move.line"

    def create_analytic_lines(self, cr, uid, ids, context=None):
        res = super(account_move_line, self).create_analytic_lines(cr, uid, ids, context=context)
        analytic_line_obj = self.pool.get('account.analytic.line')
        for move_line in self.browse(cr, uid, ids, context=context):
            # For customer invoice, link analytic line to the invoice so it is not proposed for invoicing in Bill Tasks Work
            invoice_id = move_line.invoice_id and move_line.invoice_id.type in ('out_invoice', 'out_refund') and move_line.invoice_id.id or False
            for line in move_line.analytic_line_ids:
                analytic_line_obj.write(cr, uid, line.id, {
                    'invoice_id': invoice_id,
                    'to_invoice': line.account_id.to_invoice and line.account_id.to_invoice.id or False
                    }, context=context)
        return res
