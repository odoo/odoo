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
    def _get_advance_payment_method(self):
        if self._count() == 1:
            sale_obj = self.env['sale.order']
            order = sale_obj.browse(self._context.get('active_ids'))[0]
            if all([line.product_id.invoice_policy == 'order' for line in order.order_line]) or order.invoice_count:
                return 'all'
        else:
            return 'all'
        return 'delivered'

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

    @api.model
    def _default_sale_order_id(self):
        return self._context.get('active_id')

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', default=_default_sale_order_id)
    invoice_options = fields.Char(compute="_compute_invoice_options")
    advance_payment_method = fields.Selection([
        ('delivered', 'Ready to invoice'),
        ('all', 'Ready to invoice, deduct down payments'),
        ('unbilled', 'Unbilled Total'),
        ('percentage', 'Down payment (percentage)'),
        ('fixed', 'Down payment (fixed amount)')
        ], string='What do you want to invoice?', default=_get_advance_payment_method, required=True)
    product_id = fields.Many2one('product.product', string='Down Payment Product', domain=[('type', '=', 'service')],
        default=_default_product_id)
    count = fields.Integer(default=_count, string='Order Count')
    amount = fields.Float('Down Payment Amount', digits=dp.get_precision('Account'), help="The amount to be invoiced in advance, taxes excluded.")
    deposit_account_id = fields.Many2one("account.account", string="Income Account", domain=[('deprecated', '=', False)],
        help="Account used for deposits", default=_default_deposit_account_id)
    deposit_taxes_id = fields.Many2many("account.tax", string="Customer Taxes", help="Taxes used for deposits", default=_default_deposit_taxes_id)
    currency_id = fields.Many2one(related='sale_order_id.currency_id', string='Currency')
    order_total = fields.Monetary(string='Order Total', compute='compute_all')
    upsell_downsell = fields.Monetary(string='Upsell/Downsell', compute='compute_all')
    total_to_invoice = fields.Monetary(string='Total to Invoice', compute='compute_all')
    downpayment_total = fields.Monetary(string='Down Payment', compute='compute_all')
    already_invoiced = fields.Monetary(string='Already Invoiced', compute='compute_all')
    unbilled_total = fields.Monetary(string='Unbilled Total', compute='compute_all')
    undelivered_products = fields.Monetary(string='Undelivered Products', compute='compute_all')
    ready_to_invoice = fields.Monetary(string='Ready to Invoice', compute='compute_all')
    invoiceable_line = fields.Boolean(string='Invoiceable line', compute='compute_all')

    @api.depends('sale_order_id')
    def compute_all(self):
        upsell_downsell = downpayment = unbill = undeliver = ready = so_price = invoice_price = downsell = upsell = 0.0
        for rec in self:
            already_invoiced = sum(rec.sale_order_id.invoice_ids.mapped('amount_total_signed'))
            amount_total = rec.sale_order_id.amount_total

            for line in rec.sale_order_id.order_line:
                if not line.is_downpayment:
                    if line.qty_delivered > line.product_uom_qty:
                        upsell += ((line.qty_delivered - line.product_uom_qty) * (line.price_reduce_taxinc))
                    elif line.product_id.invoice_policy == 'delivery':
                        undelivered_qty = line.product_uom_qty - (line.qty_delivered  if line.qty_delivered >= line.qty_invoiced else line.qty_invoiced)
                        undeliver += undelivered_qty * line.price_reduce_taxinc
                    if line.invoice_status == 'to invoice':
                        ready_to_invoice_qty = line.product_uom_qty if line.product_uom_qty >= line.qty_delivered else line.qty_delivered
                        ready = ready + (line.price_reduce_taxinc * (ready_to_invoice_qty - line.qty_invoiced))
                    unbilled_qty = line.product_uom_qty if line.product_uom_qty >= line.qty_delivered else line.qty_delivered
                    unbill += (line.price_reduce_taxinc * (unbilled_qty - line.qty_invoiced if unbilled_qty > 0.0 else 0.0))
                    so_price = (line.qty_invoiced * line.price_reduce_taxinc)
                    invoice_price = sum([(invoice_line.price_total) for invoice_line in line.invoice_lines])
                    downsell += (so_price - invoice_price) if invoice_price > 0.0 else 0.0
                else:
                    taxes = line.tax_id.compute_all(line.price_reduce, line.order_id.currency_id, line.qty_to_invoice, product=line.product_id, partner=line.order_id.partner_shipping_id)
                    downpayment += taxes['total_included']
            upsell_downsell = upsell - downsell

            rec.update({
                'order_total': amount_total,
                'upsell_downsell': upsell_downsell,
                'total_to_invoice': amount_total + upsell_downsell,
                'downpayment_total': downpayment,
                'already_invoiced': -(already_invoiced + downpayment),
                'unbilled_total': (unbill + downpayment),
                'undelivered_products': -undeliver,
                'invoiceable_line': True if ready > 0 else False,
                'ready_to_invoice': ready + downpayment if ready > 0 else ready
            })

    @api.depends('sale_order_id')
    def _compute_invoice_options(self):
        for rec in self:
            sale_order = rec.sale_order_id
            options = ['percentage', 'fixed']
            invoiceable_lines = sale_order.order_line.filtered(lambda line: line.invoice_status == 'to invoice')

            if invoiceable_lines.filtered(lambda x: not x.is_downpayment):
                options.append('delivered')
                if invoiceable_lines.filtered(lambda x: x.is_downpayment):
                    options.append('all')
            if sale_order.order_line.filtered(lambda line: line.invoice_status == 'no'):
                options.append('unbilled')
            rec.invoice_options = ','.join(options)

    @api.onchange('advance_payment_method')
    def onchange_advance_payment_method(self):
        if self.advance_payment_method == 'percentage':
            return {'value': {'amount': 0}}
        return {}

    @api.multi
    def _create_invoice(self, order, so_line, amount):
        inv_obj = self.env['account.invoice']
        ir_property_obj = self.env['ir.property']

        account_id = False
        if self.product_id.id:
            account_id = self.product_id.property_account_income_id.id or self.product_id.categ_id.property_account_income_categ_id.id
        if not account_id:
            inc_acc = ir_property_obj.get('property_account_income_categ_id', 'product.category')
            account_id = order.fiscal_position_id.map_account(inc_acc).id if inc_acc else False
        if not account_id:
            raise UserError(
                _('There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') %
                (self.product_id.name,))

        if self.amount <= 0.00:
            raise UserError(_('The value of the down payment amount must be positive.'))
        context = {'lang': order.partner_id.lang}
        if self.advance_payment_method == 'percentage':
            amount = order.amount_untaxed * self.amount / 100
            name = _("Down payment of %s%%") % (self.amount,)
        else:
            amount = self.amount
            name = _('Down Payment')
        del context
        taxes = self.product_id.taxes_id.filtered(lambda r: not order.company_id or r.company_id == order.company_id)
        if order.fiscal_position_id and taxes:
            tax_ids = order.fiscal_position_id.map_tax(taxes, self.product_id, order.partner_shipping_id).ids
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
                'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                'account_analytic_id': order.analytic_account_id.id or False,
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

        if self.advance_payment_method == 'delivered':
            sale_orders.action_invoice_create()
        elif self.advance_payment_method == 'all':
            sale_orders.action_invoice_create(final=True)
        elif self.advance_payment_method == 'unbilled':
            sale_orders.action_invoice_create(unbilled=True)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.config_parameter'].sudo().set_param('sale.default_deposit_product_id', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                if self.advance_payment_method == 'percentage':
                    amount = order.amount_untaxed * self.amount / 100
                else:
                    amount = self.amount
                if self.product_id.invoice_policy != 'order':
                    raise UserError(_('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(_("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                taxes = self.product_id.taxes_id.filtered(lambda r: not order.company_id or r.company_id == order.company_id)
                if order.fiscal_position_id and taxes:
                    tax_ids = order.fiscal_position_id.map_tax(taxes, self.product_id, order.partner_shipping_id).ids
                else:
                    tax_ids = taxes.ids
                context = {'lang': order.partner_id.lang}
                analytic_tag_ids = []
                for line in order.order_line:
                    analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]
                so_line = sale_line_obj.create({
                    'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                    'price_unit': amount,
                    'product_uom_qty': 0.0,
                    'order_id': order.id,
                    'discount': 0.0,
                    'product_uom': self.product_id.uom_id.id,
                    'product_id': self.product_id.id,
                    'analytic_tag_ids': analytic_tag_ids,
                    'tax_id': [(6, 0, tax_ids)],
                    'is_downpayment': True,
                })
                del context
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
            'company_id': False,
        }
