# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import groupby


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'utm.mixin']


    team_id = fields.Many2one(
        'crm.team', string='Sales Team',
        compute='_compute_team_id', store=True, readonly=False,
        ondelete="set null", tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    # UTMs - enforcing the fact that we want to 'set null' when relation is unlinked
    campaign_id = fields.Many2one(ondelete='set null')
    medium_id = fields.Many2one(ondelete='set null')
    source_id = fields.Many2one(ondelete='set null')
    sale_order_count = fields.Integer(compute="_compute_origin_so_count", string='Sale Order Count')

    def unlink(self):
        downpayment_lines = self.mapped('line_ids.sale_line_ids').filtered(lambda line: line.is_downpayment and line.invoice_lines <= self.mapped('line_ids'))
        res = super(AccountMove, self).unlink()
        if downpayment_lines:
            downpayment_lines.unlink()
        return res

    @api.depends('invoice_user_id')
    def _compute_team_id(self):
        sale_moves = self.filtered(lambda move: move.is_sale_document(include_receipts=True))
        for ((user_id, company_id), moves) in groupby(
            sale_moves,
            key=lambda m: (m.invoice_user_id.id, m.company_id.id)
        ):
            self.env['account.move'].concat(*moves).team_id = self.env['crm.team'].with_context(
                allowed_company_ids=[company_id],
            )._get_default_team_id(
                user_id=user_id,
            )

    @api.depends('line_ids.sale_line_ids')
    def _compute_origin_so_count(self):
        for move in self:
            move.sale_order_count = len(move.line_ids.sale_line_ids.order_id)

    def _reverse_moves(self, default_values_list=None, cancel=False):
        # OVERRIDE
        if not default_values_list:
            default_values_list = [{} for move in self]
        for move, default_values in zip(self, default_values_list):
            default_values.update({
                'campaign_id': move.campaign_id.id,
                'medium_id': move.medium_id.id,
                'source_id': move.source_id.id,
            })
        return super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)

    def action_post(self):
        # inherit of the function from account.move to validate a new tax and the priceunit of a downpayment
        res = super(AccountMove, self).action_post()

        # We cannot change lines content on locked SO, changes on invoices are not forwarded to the SO if the SO is locked
        dp_lines = self.line_ids.sale_line_ids.filtered(lambda l: l.is_downpayment and not l.display_type)
        dp_lines._compute_name()  # Update the description of DP lines (Draft -> Posted)
        downpayment_lines = dp_lines.filtered(lambda sol: not sol.order_id.locked)
        other_so_lines = downpayment_lines.order_id.order_line - downpayment_lines
        real_invoices = set(other_so_lines.invoice_lines.move_id)
        for so_dpl in downpayment_lines:
            so_dpl.price_unit = so_dpl._get_downpayment_line_price_unit(real_invoices)
            so_dpl.tax_id = so_dpl.invoice_lines.tax_ids

        return res

    def button_draft(self):
        res = super().button_draft()

        self.line_ids.filtered('is_downpayment').sale_line_ids.filtered(
            lambda sol: not sol.display_type)._compute_name()

        return res

    def button_cancel(self):
        res = super().button_cancel()

        self.line_ids.filtered('is_downpayment').sale_line_ids.filtered(
            lambda sol: not sol.display_type)._compute_name()

        return res

    def _post(self, soft=True):
        # OVERRIDE
        # Auto-reconcile the invoice with payments coming from transactions.
        # It's useful when you have a "paid" sale order (using a payment transaction) and you invoice it later.
        posted = super()._post(soft)

        for invoice in posted.filtered(lambda move: move.is_invoice()):
            payments = invoice.mapped('transaction_ids.payment_id').filtered(lambda x: x.state == 'in_process')
            move_lines = payments.move_id.line_ids.filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable') and not line.reconciled)
            for line in move_lines:
                invoice.js_assign_outstanding_line(line.id)
        return posted

    def _invoice_paid_hook(self):
        # OVERRIDE
        res = super(AccountMove, self)._invoice_paid_hook()
        todo = set()
        for invoice in self.filtered(lambda move: move.is_invoice()):
            for line in invoice.invoice_line_ids:
                for sale_line in line.sale_line_ids:
                    todo.add((sale_line.order_id, invoice.name))
        for (order, name) in todo:
            order.message_post(body=_("Invoice %s paid", name))
        return res

    def _action_invoice_ready_to_be_sent(self):
        # OVERRIDE
        # Make sure the send invoice CRON is called when an invoice becomes ready to be sent by mail.
        res = super()._action_invoice_ready_to_be_sent()

        send_invoice_cron = self.env.ref('sale.send_invoice_cron', raise_if_not_found=False)
        if send_invoice_cron:
            send_invoice_cron._trigger()

        return res

    def action_view_source_sale_orders(self):
        self.ensure_one()
        source_orders = self.line_ids.sale_line_ids.order_id
        result = self.env['ir.actions.act_window']._for_xml_id('sale.action_orders')
        if len(source_orders) > 1:
            result['domain'] = [('id', 'in', source_orders.ids)]
        elif len(source_orders) == 1:
            result['views'] = [(self.env.ref('sale.view_order_form', False).id, 'form')]
            result['res_id'] = source_orders.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    def _is_downpayment(self):
        # OVERRIDE
        self.ensure_one()
        return self.line_ids.sale_line_ids and all(sale_line.is_downpayment for sale_line in self.line_ids.sale_line_ids) or False

    def _get_sale_order_invoiced_amount(self, order):
        """
        Consider all lines on any invoice in self that stem from the sales order `order`. (All those invoices belong to order.company_id)
        This function returns the sum of the totals of all those lines.
        Note that this amount may be bigger than `order.amount_total`.
        """
        order_amount = 0
        for invoice in self:
            prices = sum(invoice.line_ids.filtered(lambda x: order in x.sale_line_ids.order_id).mapped('price_total'))
            order_amount += invoice.currency_id._convert(
                prices * -invoice.direction_sign,
                order.currency_id,
                invoice.company_id,
                invoice.date,
            )
        return order_amount

    def _get_partner_credit_warning_exclude_amount(self):
        # EXTENDS module 'account'
        # Consider the warning on a draft invoice created from a sales order.
        # After confirming the invoice the (partial) amount (on the invoice)
        # stemming from sales orders will be substracted from the credit_to_invoice.
        # This will reduce the total credit of the partner.
        # The computation should reflect the change of credit_to_invoice from 'res.partner'.
        # (see _compute_credit_to_invoice and _compute_amount_to_invoice from 'sale.order' )
        exclude_amount = super()._get_partner_credit_warning_exclude_amount()
        for order in self.line_ids.sale_line_ids.order_id:
            order_amount = min(self._get_sale_order_invoiced_amount(order), order.amount_to_invoice)
            order_amount_company = order.currency_id._convert(
                max(order_amount, 0),
                self.company_id.currency_id,
                self.company_id,
                fields.Date.context_today(self)
            )
            exclude_amount += order_amount_company
        return exclude_amount

    # todo need to remove both the field and compute method in master as this field is neither used in python nor in XML
    @api.depends('line_ids.sale_line_ids.order_id', 'currency_id', 'tax_totals', 'date')
    def _compute_partner_credit(self):
        super()._compute_partner_credit()
        for move in self.filtered(lambda m: m.is_invoice(include_receipts=True)):
            sale_orders = move.line_ids.sale_line_ids.order_id
            amount_total_currency = move.tax_totals['total_amount_currency']
            amount_to_invoice_currency = sum(
                sale_order.currency_id._convert(
                    sale_order.amount_to_invoice,
                    move.company_currency_id,
                    move.company_id,
                    move.date
                ) for sale_order in sale_orders
            )
            move.partner_credit += max(amount_total_currency - amount_to_invoice_currency, 0.0)
