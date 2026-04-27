# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo import  models, api, fields
from odoo.tools import format_date, clean_context


from odoo.addons.sale_subscription.models.sale_order import SUBSCRIPTION_PROGRESS_STATE


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # =============================
    #           Compute
    # =============================

    @api.depends('order_id.next_invoice_date', 'order_id.start_date')
    def _compute_qty_delivered(self):
        return super()._compute_qty_delivered()

    # =============================
    #           Utils
    # =============================

    def _get_outgoing_incoming_moves(self, strict=True):
        """ Get the moves which are related to the given period.
        """
        sub_stock = self._get_stock_subscription_lines()
        outgoing_moves, incoming_moves = super(SaleOrderLine, self - sub_stock)._get_outgoing_incoming_moves(strict)
        for line in sub_stock:
            period_start = line.order_id.last_invoice_date or line.order_id.start_date
            if  period_start and period_start == line.order_id.next_invoice_date:
                period_end = period_start + line.order_id.plan_id.billing_period
            else:
                period_end = line.order_id.next_invoice_date
            sub_outgoing_moves, sub_incoming_moves = super(SaleOrderLine, line)._get_outgoing_incoming_moves(strict)

            def date_filter(m):
                return (
                    m.date_deadline
                    and (not period_start or period_start <= m.date_deadline.date())
                    and (not period_end or m.date_deadline.date() <= period_end)
                )

            sub_outgoing_moves, sub_incoming_moves = sub_outgoing_moves.filtered(date_filter), sub_incoming_moves.filtered(date_filter)
            outgoing_moves += sub_outgoing_moves
            incoming_moves += sub_incoming_moves

        return outgoing_moves, incoming_moves

    def _get_stock_subscription_lines(self):
        """ Return the sale.order.line of self which relate to a subscription of storable products
        """
        return self.filtered(lambda line: line.recurring_invoice and line.product_id.type == 'consu')

    def _get_invoice_line_parameters(self):
        self.ensure_one()
        if self._is_postpaid_line() and self.order_id.subscription_state == '5_renewed':
            aml = self.invoice_lines.filtered(
                lambda l: l.move_id.state == 'posted' and
                       l.deferred_start_date and l.deferred_end_date and
                       l.deferred_end_date == self.last_invoiced_date)
            if aml:
                return aml[:1].deferred_start_date, aml[:1].deferred_end_date, 1, None
        return super()._get_invoice_line_parameters()

    # =============================
    #       Delivery logic
    # =============================

    def _reset_subscription_qty_to_invoice(self):
        """ Reset the quantity to deliver for this period
        """
        super(SaleOrderLine, self)._reset_subscription_qty_to_invoice()
        for line in self._get_stock_subscription_lines():
            line.write({'qty_to_deliver': line.product_uom_qty})

    def _reset_subscription_quantity_post_invoice(self):
        """ After we invoice, we close the stock.move of product invoiced based on 'delivery'
            for the period we just invoiced and launch stock rule for the next period.
        """
        stock_subscription_line = self._get_stock_subscription_lines()
        stock_subscription_line.with_context(clean_context(self._context))._action_launch_stock_rule()
        return super(SaleOrderLine, self - stock_subscription_line)._reset_subscription_quantity_post_invoice()

    def _get_lines_to_launch_stock_rule(self):
        stock_line_ids = []
        for line in self:
            if not line.recurring_invoice or line.order_id.subscription_state == '7_upsell':
                # regular lines
                stock_line_ids.append(line.id)
            elif line.qty_invoiced and line.last_invoiced_date:
                # invoiced line (move posted)
                stock_line_ids.append(line.id)
            elif line.order_id.subscription_state in SUBSCRIPTION_PROGRESS_STATE and not line.last_invoiced_date:
                # prepaid and postpaid lines not already invoiced
                stock_line_ids.append(line.id)
            elif line._is_postpaid_line() and line.last_invoiced_date:
                # postpaid already invoiced
                stock_line_ids.append(line.id)
        return self.env['sale.order.line'].browse(stock_line_ids)

    def _action_launch_stock_rule(self, **kwargs):
        """ Only launch stock rule if we know they won't be empty
        """
        lines = self._get_lines_to_launch_stock_rule()
        return super(SaleOrderLine, lines)._action_launch_stock_rule(**kwargs)

    @api.model
    def _get_incoming_outgoing_moves_filter(self):
        """Check subscription moves in/out during invoice period."""
        base_filter = super()._get_incoming_outgoing_moves_filter()
        if self.recurring_invoice:
            so = self.order_id
            start = so.last_invoice_date or so.start_date
            end = so.next_invoice_date

            def date_filter(m):
                return m.date_deadline and start and end and start <= m.date_deadline.date() < end
            return {
                'incoming_moves': lambda m: base_filter['incoming_moves'](m) and date_filter(m),
                'outgoing_moves': lambda m: base_filter['outgoing_moves'](m) and date_filter(m)
            }
        return base_filter

    def _get_qty_procurement(self, previous_product_uom_qty=False):
        """ Compute the quantity that was already delivered for the current period.
        """
        self.ensure_one()
        # If we update the line, we don't want it to affect the current period for subscriptions
        if self.recurring_invoice and previous_product_uom_qty and previous_product_uom_qty.get(self.id, 0):
            return self.product_uom_qty
        return super()._get_qty_procurement(previous_product_uom_qty=previous_product_uom_qty)

    def _prepare_procurement_values(self, group_id=False):
        """ Update move.line values
        We use product_description_variants to display the invoicing date
        Ensure one is present in inherited function
        """
        values = super()._prepare_procurement_values(group_id)
        if not self.recurring_invoice or self.order_id.subscription_state == '7_upsell':
            return values
        # Remove 1 day as normal people thinks in terms of inclusive ranges.
        if not self.order_id.start_date or self.order_id.next_invoice_date == self.order_id.start_date and not self.order_id.last_invoice_date:
            current_deadline = self.order_id.next_invoice_date + self.order_id.plan_id.billing_period - relativedelta(days=1)
        else:
            current_deadline = self.order_id.next_invoice_date - relativedelta(days=1)

        current_period_start = self.order_id.last_invoice_date or self.order_id.start_date or fields.Date.today()
        lang_code = self.order_id.partner_id.lang
        format_start = format_date(self.env, current_period_start, lang_code=lang_code)
        format_end = format_date(self.env, current_deadline, lang_code=lang_code)
        values.update({
            'date_planned': current_period_start,
            'date_deadline': current_deadline,
            'product_description_variants': f'{values.get("product_description_variants", "")}\n{format_start} to {format_end}',
        })
        return values
