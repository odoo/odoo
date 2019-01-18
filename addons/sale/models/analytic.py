# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    so_line = fields.Many2one('sale.order.line', string='Sales Order Line')

    @api.model
    def create(self, values):
        result = super(AccountAnalyticLine, self).create(values)
        result._sale_postprocess(values)
        return result

    @api.multi
    def write(self, values):
        # get current so lines for which update qty wil be required
        sale_order_lines = self.env['sale.order.line']
        if 'so_line' in values:
            sale_order_lines = self.sudo().mapped('so_line')
        result = super(AccountAnalyticLine, self).write(values)
        self._sale_postprocess(values, additional_so_lines=sale_order_lines)
        return result

    @api.multi
    def unlink(self):
        sale_order_lines = self.sudo().mapped('so_line')
        res = super(AccountAnalyticLine, self).unlink()
        sale_order_lines.with_context(sale_analytic_force_recompute=True)._analytic_compute_delivered_quantity()
        return res

    @api.model
    def _sale_get_fields_delivered_qty(self):
        """ Returns a list with the field impacting the delivered quantity on SO line. """
        return ['so_line', 'unit_amount', 'product_uom_id']

    @api.multi
    def _sale_postprocess(self, values, additional_so_lines=None):
        if 'so_line' not in values:  # allow to force a False value for so_line
            # only take the AAL from expense or vendor bill, meaning having a negative amount
            self.filtered(lambda aal: aal.amount <= 0).with_context(sale_analytic_norecompute=True)._sale_determine_order_line()

        if any(field_name in values for field_name in self._sale_get_fields_delivered_qty()):
            if not self._context.get('sale_analytic_norecompute'):
                so_lines = self.sudo().filtered(lambda aal: aal.so_line).mapped('so_line')
                if additional_so_lines:
                    so_lines |= additional_so_lines
                so_lines.sudo()._analytic_compute_delivered_quantity()

    # NOTE JEM: thoses method are used in vendor bills to reinvoice at cost (see test `test_cost_invoicing`)
    # some cleaning are still necessary

    @api.multi
    def _sale_get_invoice_price(self, order):
        self.ensure_one()
        if self.product_id.expense_policy == 'sales_price':
            return self.product_id.with_context(
                partner=order.partner_id.id,
                date_order=order.date_order,
                pricelist=order.pricelist_id.id,
                uom=self.product_uom_id.id
            ).price
        if self.unit_amount == 0.0:
            return 0.0

        # Prevent unnecessary currency conversion that could be impacted by exchange rate
        # fluctuations
        if self.currency_id and self.amount_currency and self.currency_id == order.currency_id:
            return abs(self.amount_currency / self.unit_amount)

        price_unit = abs(self.amount / self.unit_amount)
        currency_id = self.company_id.currency_id
        if currency_id and currency_id != order.currency_id:
            price_unit = currency_id.compute(price_unit, order.currency_id)
        return price_unit

    @api.multi
    def _sale_prepare_sale_order_line_values(self, order, price):
        self.ensure_one()
        last_so_line = self.env['sale.order.line'].search([('order_id', '=', order.id)], order='sequence desc', limit=1)
        last_sequence = last_so_line.sequence + 1 if last_so_line else 100

        fpos = order.fiscal_position_id or order.partner_id.property_account_position_id
        taxes = fpos.map_tax(self.product_id.taxes_id, self.product_id, order.partner_id)

        return {
            'order_id': order.id,
            'name': self.name,
            'sequence': last_sequence,
            'price_unit': price,
            'tax_id': [x.id for x in taxes],
            'discount': 0.0,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': 0.0,
            'qty_delivered': self.unit_amount,
        }

    @api.multi
    def _sale_determine_order(self):
        mapping = {}
        for analytic_line in self.sudo().filtered(lambda aal: not aal.so_line and aal.product_id and aal.product_id.expense_policy not in [False, 'no']):
            sale_order = self.env['sale.order'].search([('analytic_account_id', '=', analytic_line.account_id.id), ('state', '=', 'sale')], limit=1)
            if not sale_order:
                sale_order = self.env['sale.order'].search([('analytic_account_id', '=', analytic_line.account_id.id)], limit=1)
            if not sale_order:
                continue
            mapping[analytic_line.id] = sale_order
        return mapping

    @api.multi
    def _sale_determine_order_line(self):
        """ Automatically set the SO line on the analytic line, for the expense/vendor bills flow. It retrives
            an existing line, or create a new one (upselling expenses).
        """
        # determine SO : first SO open linked to AA
        sale_order_map = self._sale_determine_order()
        # determine so line
        for analytic_line in self.sudo().filtered(lambda aal: not aal.so_line and aal.product_id and aal.product_id.expense_policy not in [False, 'no']):
            sale_order = sale_order_map.get(analytic_line.id)
            if not sale_order:
                continue

            if sale_order.state != 'sale':
                message_unconfirmed = _('The Sales Order %s linked to the Analytic Account %s must be validated before registering expenses.')
                messages = {
                    'draft': message_unconfirmed,
                    'sent': message_unconfirmed,
                    'done': _('The Sales Order %s linked to the Analytic Account %s is currently locked. You cannot register an expense on a locked Sales Order. Please create a new SO linked to this Analytic Account.'),
                    'cancel': _('The Sales Order %s linked to the Analytic Account %s is cancelled. You cannot register an expense on a cancelled Sales Order.'),
                }
                raise UserError(messages[sale_order.state] % (sale_order.name, analytic_line.account_id.name))

            price = analytic_line._sale_get_invoice_price(sale_order)
            so_line = None
            if analytic_line.product_id.expense_policy == 'sales_price' and analytic_line.product_id.invoice_policy == 'delivery':
                so_line = self.env['sale.order.line'].search([
                    ('order_id', '=', sale_order.id),
                    ('price_unit', '=', price),
                    ('product_id', '=', self.product_id.id)
                ], limit=1)

            if not so_line:
                # generate a new SO line
                so_line_values = analytic_line._sale_prepare_sale_order_line_values(sale_order, price)
                so_line = self.env['sale.order.line'].create(so_line_values)
                so_line._compute_tax_id()
            else:
                so_line.write({'qty_delivered': so_line.qty_delivered + analytic_line.unit_amount})

            if so_line:  # if so line found or created, then update AAL (this will trigger the recomputation of qty delivered on SO line)
                analytic_line.with_context(sale_analytic_norecompute=True).write({'so_line': so_line.id})
