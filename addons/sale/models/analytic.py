# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    def _default_sale_line_domain(self):
        """ This is only used for delivered quantity of SO line based on analytic line, and timesheet
            (see sale_timesheet). This can be override to allow further customization.
        """
        return [('qty_delivered_method', '=', 'analytic')]

    so_line = fields.Many2one('sale.order.line', string='Sales Order Item', domain=lambda self: self._default_sale_line_domain())

    @api.model
    def create(self, values):
        result = super(AccountAnalyticLine, self).create(values)
        if 'so_line' not in values and not result.so_line and result.product_id and result.product_id.expense_policy != 'no' and result.amount <= 0:  # allow to force a False value for so_line
            result.sudo()._sale_determine_order_line()
        return result

    @api.multi
    def write(self, values):
        result = super(AccountAnalyticLine, self).write(values)
        if 'so_line' not in values:  # allow to force a False value for so_line
            # only take the AAL from expense or vendor bill, meaning having a negative amount
            self.sudo().filtered(lambda aal: not aal.so_line and aal.product_id and aal.product_id.expense_policy != 'no' and aal.amount <= 0)._sale_determine_order_line()

    # ----------------------------------------------------------
    # Vendor Bill / Expense : determine the Sale Order to reinvoice
    # ----------------------------------------------------------

    @api.multi
    def _sale_get_invoice_price(self, order):
        self.ensure_one()
        if self.product_id.expense_policy == 'sales_price':
            return self.product_id.with_context(
                partner=order.partner_id,
                date_order=order.date_order,
                pricelist=order.pricelist_id.id,
                uom=self.product_uom_id.id
            ).price
        if self.unit_amount == 0.0:
            return 0.0

        # Prevent unnecessary currency conversion that could be impacted by exchange rate
        # fluctuations
        if self.currency_id and self.amount and self.currency_id == order.currency_id:
            return abs(self.amount / self.unit_amount)

        price_unit = abs(self.amount / self.unit_amount)
        currency_id = self.company_id.currency_id
        if currency_id and currency_id != order.currency_id:
            price_unit = currency_id._convert(
                price_unit, order.currency_id, order.company_id, order.date_order or fields.Date.today())
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
            'is_expense': True,
        }

    @api.multi
    def _sale_determine_order(self):
        mapping = {}
        for analytic_line in self:
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
        value_to_write = {}
        for analytic_line in self:
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

            so_line = None
            price = analytic_line._sale_get_invoice_price(sale_order)
            if analytic_line.product_id.expense_policy == 'sales_price' and analytic_line.product_id.invoice_policy == 'delivery':
                so_line = self.env['sale.order.line'].search([
                    ('order_id', '=', sale_order.id),
                    ('price_unit', '=', price),
                    ('product_id', '=', self.product_id.id),
                    ('is_expense', '=', True),
                ], limit=1)

            if not so_line:
                # generate a new SO line
                so_line_values = analytic_line._sale_prepare_sale_order_line_values(sale_order, price)
                so_line = self.env['sale.order.line'].create(so_line_values)
                so_line._compute_tax_id()

            if so_line:  # if so line found or created, then update AAL (this will trigger the recomputation of qty delivered on SO line)
                value_to_write.setdefault(so_line.id, self.env['account.analytic.line'])
                value_to_write[so_line.id] |= analytic_line

        # write so line on (maybe) multiple AAL to trigger only one read_group per SO line
        for so_line_id, analytic_lines in value_to_write.items():
            if analytic_lines:
                analytic_lines.write({'so_line': so_line_id})
