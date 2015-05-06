# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta

from openerp import api, fields, models


class sale_order(models.Model):
    _inherit = "sale.order"
    _name = "sale.order"

    def create_contract(self):
        """ Create a contract based on the order's quote template's contract template """
        self.ensure_one()
        if self.require_payment:
            tx = self.env['payment.transaction'].search([('reference', '=', self.name)])
            payment_method = self.env['payment.method'].search([('acquirer_ref', '=', tx.partner_reference)])
        if self.template_id and self.template_id.contract_template and not self.project_id:
            values = {
                'name': self.template_id.contract_template.name,
                'state': 'open',
                'type': 'contract',
                'template_id': self.template_id.contract_template.id,
                'partner_id': self.partner_id.id,
                'manager_id': self.user_id.id,
                'parent_id': self.template_id.contract_template.parent_id.id,
                'contract_type': self.template_id.contract_template.contract_type,
                'date_start': fields.Date.today(),
                'quantity_max': self.template_id.contract_template.quantity_max,
                'parent_id': self.template_id.contract_template.parent_id and self.template_id.contract_template.parent_id.id or False,
                'description': self.template_id.contract_template.description,
                'fix_price_invoices': self.template_id.contract_template.fix_price_invoices,
                'amount_max': self.template_id.contract_template.amount_max,
                'invoice_on_timesheets': self.template_id.contract_template.invoice_on_timesheets,
                'hours_qtt_est': self.template_id.contract_template.hours_qtt_est,
                'to_invoice': self.template_id.contract_template.to_invoice.id,
                'pricelist_id': self.partner_id.property_product_pricelist.id,
                'user_closable': self.template_id.contract_template.user_closable,
                'payment_method_id': payment_method and payment_method.id if self.require_payment else False,
            }
            if 'asset_category_id' in self.template_id.contract_template._fields:
                values.update({'asset_category_id': self.template_id.contract_template.asset_category_id.id})
            if values['contract_type'] == 'subscription':
                values.update({
                    'recurring_rule_type': self.template_id.contract_template.recurring_rule_type,
                    'recurring_interval': self.template_id.contract_template.recurring_interval,
                })
                # compute the next invoice date
                today = datetime.date.today()
                periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
                invoicing_period = relativedelta(**{periods[values['recurring_rule_type']]: values['recurring_interval']})
                recurring_next_date = today + invoicing_period
                values['recurring_next_date'] = fields.Date.to_string(recurring_next_date)

            account = self.env['account.analytic.account'].sudo().create(values)
            account.name = self.partner_id.name + ' - ' + account.code

            invoice_line_ids = []
            for line in self.order_line:
                if line.product_id.recurring_invoice:
                    invoice_line_ids.append((0, 0, {
                        'product_id': line.product_id.id,
                        'analytic_account_id': account.id,
                        'name': line.name,
                        'quantity': line.product_uom_qty,
                        'discount': line.discount,
                        'uom_id': line.product_uom.id,
                        'price_unit': line.price_unit,
                    }))
            if invoice_line_ids:
                analytic_values = {'recurring_invoice_line_ids': invoice_line_ids}
                account.write(analytic_values)

            self.project_id = account
            return account
        return True

    @api.one
    def action_button_confirm(self):
        res = super(sale_order, self).action_button_confirm()
        self.create_contract()
        return res

    # DBO: the following is there to amend the behaviour of website_sale:
    # - do not update price on sale_order_line where force_price = True
    #   (some options may have prices that are different from the product price)
    # - prevent having a cart with options for different contracts (project_id)
    # If we ever decide to move the payment code out of website_sale, we should scrap all this
    def set_project_id(self, account_id):
        """ Set the specified account_id account.analytic.account as the sale_order project_id
        and remove all the recurring products from the sale order if the field was already defined"""
        data = []
        account = self.env['account.analytic.account'].browse(account_id)
        if self.project_id != account:
            self.reset_project_id()
        self.write({'project_id': account.id, 'user_id': account.manager_id.id if account.manager_id else False})

    def reset_project_id(self):
        """ Remove the project_id of the sale order and remove all sale.order.line whose
        product is recurring"""
        data = []
        for line in self.order_line:
            if line.product_id.product_tmpl_id.recurring_invoice:
                data.append((2, line.id))
        self.write({'order_line': data, 'project_id': False})

    def _website_product_id_change(self, cr, uid, ids, order_id, product_id, qty=0, line_id=None, context=None):
        res = super(sale_order, self)._website_product_id_change(cr, uid, ids, order_id, product_id, qty, line_id, context=context)
        if line_id:
            line = self.pool['sale.order.line'].browse(cr, uid, line_id, context=context)
            if line.force_price:
                forced_price = line.price_unit
                res['price_unit'] = forced_price
        return res


class sale_order_line(models.Model):
    _inherit = "sale.order.line"
    _name = "sale.order.line"

    force_price = fields.Boolean('Force price', help='Force a specific price, regardless of any coupons or pricelist change', default=False)

    @api.multi
    def button_confirm(self):
        for line in self:
            if line.order_id.project_id and line.product_id.recurring_invoice:
                line.order_id.project_id.message_post(body="""
                    <div>New Option added by Sale Order confirmation</div>
                    <div>&nbsp;&nbsp;&bull; <b>Option</b>: """+line.product_id.name_template+"""</div>
                    <div>&nbsp;&nbsp;&bull; <b>Sale Order</b>: """+line.order_id.name+"""</div>
                    <div>&nbsp;&nbsp;&bull; <b>Recurring Price</b>: """+str(line.price_unit)+"""</div>
                    <div>&nbsp;&nbsp;&bull; <b>Discount (partial invoicing period)</b>: """+str(line.discount)+"""</div>
                    <div>&nbsp;&nbsp;&bull; <b>Discounted Price</b>: """+str(line.price_subtotal)+"""</div>
                    """)
        return super(sale_order_line, self).button_confirm()

    @api.model
    def _prepare_order_line_invoice_line(self, line, account_id=False):
        res = super(sale_order_line, self)._prepare_order_line_invoice_line(line, account_id=account_id)
        if 'asset_category_id' in self.env['account.analytic.account']._fields:
            if line.order_id.template_id and line.order_id.template_id.contract_template:
                if line.order_id.template_id.contract_template.asset_category_id and line.product_id.recurring_invoice:
                    res.update({'asset_category_id': line.order_id.template_id.contract_template.asset_category_id.id})
        return res
