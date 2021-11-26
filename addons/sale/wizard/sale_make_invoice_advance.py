# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import time

from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _name = "sale.advance.payment.inv"
    _description = "Sales Advance Payment Invoice"

    @api.model
    def _count(self):
        return len(self._context.get('active_ids', []))

    @api.model
    def _default_product_id(self):
        product_id = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
        return self.env['product.product'].browse(int(product_id)).exists()

    @api.model
    def _default_deposit_account_id(self):
        return self._default_product_id()._get_product_accounts()['income']

    @api.model
    def _default_deposit_taxes_id(self):
        return self._default_product_id().taxes_id

    @api.model
    def _default_has_down_payment(self):
        if self._context.get('active_model') == 'sale.order' and self._context.get('active_id', False):
            sale_order = self.env['sale.order'].browse(self._context.get('active_id'))
            return sale_order.order_line.filtered(
                lambda sale_order_line: sale_order_line.is_downpayment
            )

        return False

    @api.model
    def _default_currency_id(self):
        if self._context.get('active_model') == 'sale.order' and self._context.get('active_id', False):
            sale_order = self.env['sale.order'].browse(self._context.get('active_id'))
            return sale_order.currency_id

    advance_payment_method = fields.Selection([
        ('delivered', 'Regular invoice'),
        ('percentage', 'Down payment (percentage)'),
        ('fixed', 'Down payment (fixed amount)')
        ], string='Create Invoice', default='delivered', required=True,
        help="A standard invoice is issued with all the order lines ready for invoicing, \
        according to their invoicing policy (based on ordered or delivered quantity).")
    deduct_down_payments = fields.Boolean('Deduct down payments', default=True)
    has_down_payments = fields.Boolean('Has down payments', default=_default_has_down_payment, readonly=True)
    product_id = fields.Many2one('product.product', string='Down Payment Product', domain=[('type', '=', 'service')],
        default=_default_product_id)
    count = fields.Integer(default=_count, string='Order Count')
    amount = fields.Float('Down Payment Amount', digits='Account', help="The percentage of amount to be invoiced in advance, taxes excluded.")
    currency_id = fields.Many2one('res.currency', string='Currency', default=_default_currency_id)
    fixed_amount = fields.Monetary('Down Payment Amount (Fixed)', help="The fixed amount to be invoiced in advance, taxes excluded.")
    deposit_account_id = fields.Many2one("account.account", string="Income Account", domain=[('deprecated', '=', False)],
        help="Account used for deposits", default=_default_deposit_account_id)
    deposit_taxes_id = fields.Many2many("account.tax", string="Customer Taxes", help="Taxes used for deposits", default=_default_deposit_taxes_id)

    @api.onchange('advance_payment_method')
    def onchange_advance_payment_method(self):
        if self.advance_payment_method == 'percentage':
            amount = self.default_get(['amount']).get('amount')
            return {'value': {'amount': amount}}
        return {}

    def _prepare_invoice_values(self, order, so_lines):
        invoice_lines_vals = []
        for line in so_lines:
            name = ' '.join([line.name] + [tax.name for tax in line.tax_id])
            invoice_lines_vals.append(Command.create({
                'name': name,
                'price_unit': line.price_unit,
                'quantity': 1.0,
                'product_id': self.product_id.id,
                'product_uom_id': line.product_uom.id,
                'tax_ids': [Command.set(line.tax_id.ids)],
                'sale_line_ids': [Command.set([line.id])],
                'analytic_tag_ids': [Command.set(line.analytic_tag_ids.ids)],
                'analytic_account_id': order.analytic_account_id.id or False,
            }))

        invoice_vals = {
            'ref': order.client_order_ref,
            'move_type': 'out_invoice',
            'invoice_origin': order.name,
            'invoice_user_id': order.user_id.id,
            'narration': order.note,
            'partner_id': order.partner_invoice_id.id,
            'fiscal_position_id': (order.fiscal_position_id or order.fiscal_position_id._get_fiscal_position(order.partner_id)).id,
            'partner_shipping_id': order.partner_shipping_id.id,
            'currency_id': order.pricelist_id.currency_id.id,
            'payment_reference': order.reference,
            'invoice_payment_term_id': order.payment_term_id.id,
            'partner_bank_id': order.company_id.partner_id.bank_ids[:1].id,
            'team_id': order.team_id.id,
            'campaign_id': order.campaign_id.id,
            'medium_id': order.medium_id.id,
            'source_id': order.source_id.id,
            'invoice_line_ids': invoice_lines_vals,
        }

        return invoice_vals

    def _get_advance_amount(self, order):
        if self.advance_payment_method == 'percentage':
            amount = order.amount_total * self.amount / 100
        else:
            amount = self.fixed_amount
        if amount <= 0.00:
            raise UserError(_('The value of the down payment amount must be positive.'))

        return amount

    def _create_invoice(self, order, so_lines):
        invoice_vals = self._prepare_invoice_values(order, so_lines)

        invoice = self.env['account.move'].with_company(order.company_id)\
            .sudo().create(invoice_vals).with_user(self.env.uid)
        invoice.message_post_with_view('mail.message_origin_link',
                    values={'self': invoice, 'origin': order},
                    subtype_id=self.env.ref('mail.mt_note').id)
        return invoice

    def _prepare_so_line(self, order, analytic_tag_ids, tax_ids, amount):
        context = {'lang': order.partner_id.lang}
        so_values = {
            'name': _('Down Payment: %s') % (time.strftime('%m %Y'),),
            'price_unit': amount,
            'product_uom_qty': 0.0,
            'order_id': order.id,
            'discount': 0.0,
            'product_uom': self.product_id.uom_id.id,
            'product_id': self.product_id.id,
            'analytic_tag_ids': analytic_tag_ids,
            'tax_id': [Command.set(tax_ids)] if tax_ids else [],
            'is_downpayment': True,
            'sequence': order.order_line and order.order_line[-1].sequence + 1 or 10,
        }
        del context
        return so_values

    def _create_invoices(self, sale_orders):
        if self.advance_payment_method == 'delivered':
            return sale_orders._create_invoices(final=self.deduct_down_payments)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.config_parameter'].sudo().set_param('sale.default_deposit_product_id', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            invoices = self.env['account.move']
            for order in sale_orders:

                if self.product_id.invoice_policy != 'order':
                    raise UserError(_('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(_("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))


                advance_amount = self._get_advance_amount(order)
                group_by_taxes = defaultdict(lambda: {
                    'lines': self.env['sale.order.line'],
                    'sum_price_reduce_x_quantity': 0.0,
                    'sum_price_subtotal': 0.0,
                    'sum_price_total': 0.0,
                })
                if any(tax.amount_type == 'fixed' for tax in order.order_line.tax_id.flatten_taxes_hierarchy()):
                    # no breakdown per taxes if any tax with amount type "fixed"
                    group_by_taxes[None]['lines'] = order.order_line
                else:
                    for line in order.order_line:
                        tax_ids = tuple(sorted(line.tax_id.ids))
                        group_by_taxes[tax_ids]['lines'] += line
                        group_by_taxes[tax_ids]['sum_price_reduce_x_quantity'] += line.price_unit * (1.0 - line.discount / 100.0) * line.product_uom_qty  # "price_reduce" field not used because already rounded
                        group_by_taxes[tax_ids]['sum_price_subtotal'] += line.price_subtotal
                        group_by_taxes[tax_ids]['sum_price_total'] += line.price_total

                total_amount_left = advance_amount
                so_line_values = []
                group_by_taxes_items = list(group_by_taxes.items())
                last_group = group_by_taxes_items[-1][1]
                for tax_ids, group in group_by_taxes_items:
                    analytic_tag_ids = [Command.set(group['lines'].analytic_tag_ids.ids)]

                    if group == last_group:
                        # last line : set total_amount_left to correct any rounding error that might have appeared
                        so_line_amount_tax_incl = total_amount_left
                    else:
                        so_line_amount_tax_incl = advance_amount * (group['sum_price_total'] / order.amount_total)
                        total_amount_left -= so_line_amount_tax_incl

                    if tax_ids:
                        so_line_amount_tax_excl = (
                            # amount tax incl ...
                            so_line_amount_tax_incl *
                            # ... divided to get tax exclude ...
                            (group['sum_price_subtotal'] / group['sum_price_total']) *
                            # ... adapt price unit if tax include
                            (group['sum_price_reduce_x_quantity'] / group['sum_price_subtotal'])
                        )
                    else:
                        so_line_amount_tax_excl = so_line_amount_tax_incl

                    so_line_values.append(self._prepare_so_line(
                        order,
                        analytic_tag_ids,
                        tax_ids,
                        so_line_amount_tax_excl
                    ))
                so_lines = sale_line_obj.create(so_line_values)
                invoices += self._create_invoice(order, so_lines)
            return invoices

    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
        self._create_invoices(sale_orders)
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
