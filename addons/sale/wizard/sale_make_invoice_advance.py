# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _name = "sale.advance.payment.inv"
    _description = "Sales Advance Payment Invoice"

    @api.model
    def _count(self):
        return len(self._context.get('active_ids', []))

    @api.model
    def _get_deduct_down_payment(self):
        if self._count() == 1:
            order = self.env['sale.order'].browse(self._context.get('active_id'))
            if all([line.product_id.invoice_policy == 'order' for line in order.order_line]) or order.invoice_count:
                return True
        return False

    @api.model
    def _default_product_id(self):
        product_id = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
        return self.env['product.product'].browse(int(product_id))

    @api.model
    def _default_deposit_account_id(self):
        return self._default_product_id().property_account_income_id

    @api.model
    def _default_deposit_taxes_id(self):
        return self._default_product_id().taxes_id

    @api.depends('advance_payment_method', 'deduct_down_payment')
    def _get_invoiceable_amount(self):
        order = self.env['sale.order'].browse(self._context.get('active_id'))
        total_amount = 0
        for line in order.order_line.filtered(lambda x: x.invoice_status == 'to invoice'):
            if not self.deduct_down_payment and line.is_downpayment:
                continue
            taxes = line.tax_id.compute_all(line.price_reduce, line.order_id.currency_id, line.qty_to_invoice, product=line.product_id, partner=line.order_id.partner_shipping_id)
            total_amount += taxes['total_included']
        self.invoiceable_amount = total_amount

    @api.multi
    def _get_default_currency(self):
        return self.env['sale.order'].browse(self._context.get('active_id')).currency_id

    @api.depends('advance_payment_method')
    def _get_down_payment(self):
        order = self.env['sale.order'].browse(self._context.get('active_id'))
        self.total_down_payment = sum(line.price_unit for line in order.order_line.filtered(lambda x: x.is_downpayment and x.invoice_status == 'to invoice'))

    advance_payment_method = fields.Selection([
        ('invoiceable', 'Invoiceable lines'),
        ('down_payment', 'Down payments'),
        ('all_uninvoiced', 'All the lines not yet invoiced')], string='What do you want to invoice?', default='invoiceable', required=True)
    product_id = fields.Many2one('product.product', string='Down payment product', domain=[('type', '=', 'service')], default=_default_product_id)
    down_payment_method = fields.Selection([('percentage', 'Percentage'), ('fixed', 'Fixed amount')], default='percentage', required=True)
    deduct_down_payment = fields.Boolean('Deduct down payments', default=_get_deduct_down_payment)
    currency_id = fields.Many2one('res.currency', default=_get_default_currency, readonly=True)
    total_down_payment = fields.Monetary(compute='_get_down_payment', digits=dp.get_precision('Account'), string='Total paid down payment amount', readonly=True, currency_field='currency_id')
    invoiceable_amount = fields.Monetary(compute='_get_invoiceable_amount', digits=dp.get_precision('Account'), string='Total Invoiceable amount', readonly=True, currency_field='currency_id')
    count = fields.Integer(default=_count, string='# of Orders')
    amount = fields.Float('Down Payment Amount', digits=dp.get_precision('Account'), help="The amount to be invoiced in advance, taxes excluded.")
    deposit_account_id = fields.Many2one("account.account", string="Income Account", domain=[('deprecated', '=', False)],
        help="Account used for deposits", default=_default_deposit_account_id)
    deposit_taxes_id = fields.Many2many("account.tax", string="Customer Taxes", help="Taxes used for deposits", default=_default_deposit_taxes_id)

    @api.onchange('down_payment_method')
    def onchange_down_payment_method(self):
        self.amount = False

    @api.multi
    def _create_invoice(self, order, so_line, amount):
        inv_obj = self.env['account.invoice']
        ir_property_obj = self.env['ir.property']

        account_id = False
        if self.product_id.id:
            account_id = self.product_id.property_account_income_id.id
        if not account_id:
            inc_acc = ir_property_obj.get('property_account_income_categ_id', 'product.category')
            account_id = order.fiscal_position_id.map_account(inc_acc).id if inc_acc else False
        if not account_id:
            raise UserError(
                _('There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') %
                (self.product_id.name,))

        if self.amount <= 0.00:
            raise UserError(_('The value of the down payment amount must be positive.'))
        if self.advance_payment_method == 'down_payment' and self.down_payment_method == 'percentage':
            amount = order.amount_untaxed * self.amount / 100
            name = _("Down payment of %s%%") % (self.amount,)
        else:
            amount = self.amount
            name = _('Down Payment')
        taxes = self.product_id.taxes_id.filtered(lambda r: not order.company_id or r.company_id == order.company_id)
        if order.fiscal_position_id and taxes:
            tax_ids = order.fiscal_position_id.map_tax(taxes).ids
        else:
            tax_ids = taxes.ids

        invoice = inv_obj.create({
            'name': order.client_order_ref or order.name,
            'origin': order.name,
            'type': 'out_invoice',
            'reference': False,
            'account_id': order.partner_id.property_account_receivable_id.id,
            'partner_id': order.partner_invoice_id.id,
            'partner_shipping_id': order.partner_shipping_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': name,
                'origin': order.name,
                'account_id': account_id,
                'price_unit': amount,
                'quantity': 1.0,
                'discount': 0.0,
                'uom_id': self.product_id.uom_id.id,
                'product_id': self.product_id.id,
                'sale_line_ids': [(6, 0, [so_line.id])],
                'invoice_line_tax_ids': [(6, 0, tax_ids)],
                'account_analytic_id': order.project_id.id or False,
            })],
            'currency_id': order.pricelist_id.currency_id.id,
            'payment_term_id': order.payment_term_id.id,
            'fiscal_position_id': order.fiscal_position_id.id or order.partner_id.property_account_position_id.id,
            'team_id': order.team_id.id,
            'user_id': order.user_id.id,
            'comment': order.note,
        })
        invoice.compute_taxes()
        invoice.message_post_with_view('mail.message_origin_link',
                    values={'self': invoice, 'origin': order},
                    subtype_id=self.env.ref('mail.mt_note').id)
        return invoice

    @api.multi
    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))

        if self.advance_payment_method == 'invoiceable':
            sale_orders.action_invoice_create(final=self.deduct_down_payment)
        elif self.advance_payment_method == 'all_uninvoiced':
            sale_orders.action_invoice_create(all_uninvoiced=True)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.config_parameter'].sudo().set_param('sale.default_deposit_product_id', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                if self.advance_payment_method == 'down_payment' and self.down_payment_method == 'percentage':
                    amount = order.amount_untaxed * self.amount / 100
                else:
                    amount = self.amount
                if self.product_id.invoice_policy != 'order':
                    raise UserError(_('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(_("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                taxes = self.product_id.taxes_id.filtered(lambda r: not order.company_id or r.company_id == order.company_id)
                if order.fiscal_position_id and taxes:
                    tax_ids = order.fiscal_position_id.map_tax(taxes).ids
                else:
                    tax_ids = taxes.ids
                so_line = sale_line_obj.create({
                    'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                    'price_unit': amount,
                    'product_uom_qty': 0.0,
                    'order_id': order.id,
                    'discount': 0.0,
                    'product_uom': self.product_id.uom_id.id,
                    'product_id': self.product_id.id,
                    'tax_id': [(6, 0, tax_ids)],
                    'is_downpayment': True,
                })
                self._create_invoice(order, so_line, amount)
        if self._context.get('open_invoices', False):
            return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}

    def _prepare_deposit_product(self):
        return {
            'name': 'Down payment',
            'type': 'service',
            'invoice_policy': 'order',
            'property_account_income_id': self.deposit_account_id.id,
            'taxes_id': [(6, 0, self.deposit_taxes_id.ids)],
        }
