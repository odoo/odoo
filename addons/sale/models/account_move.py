# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'utm.mixin']

    @api.model
    def _get_invoice_default_sale_team(self):
        return self.env['crm.team']._get_default_team_id()

    team_id = fields.Many2one(
        'crm.team', string='Sales Team', default=_get_invoice_default_sale_team,
        ondelete="set null", tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    partner_shipping_id = fields.Many2one(
        'res.partner',
        string='Delivery Address',
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Delivery address for current invoice.")

    @api.onchange('partner_shipping_id', 'company_id')
    def _onchange_partner_shipping_id(self):
        """
        Trigger the change of fiscal position when the shipping address is modified.
        """
        delivery_partner_id = self._get_invoice_delivery_partner_id()
        fiscal_position = self.env['account.fiscal.position'].with_company(self.company_id).get_fiscal_position(
            self.partner_id.id, delivery_id=delivery_partner_id)

        if fiscal_position:
            self.fiscal_position_id = fiscal_position

    def unlink(self):
        downpayment_lines = self.mapped('line_ids.sale_line_ids').filtered(lambda line: line.is_downpayment and line.invoice_lines <= self.mapped('line_ids'))
        res = super(AccountMove, self).unlink()
        if downpayment_lines:
            downpayment_lines.unlink()
        return res

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        # OVERRIDE
        # Recompute 'partner_shipping_id' based on 'partner_id'.
        addr = self.partner_id.address_get(['delivery'])
        self.partner_shipping_id = addr and addr.get('delivery')

        res = super(AccountMove, self)._onchange_partner_id()

        return res

    @api.onchange('invoice_user_id')
    def onchange_user_id(self):
        if self.invoice_user_id and self.invoice_user_id.sale_team_id:
            self.team_id = self.env['crm.team']._get_default_team_id(user_id=self.invoice_user_id.id, domain=[('company_id', '=', self.company_id.id)])

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
        #inherit of the function from account.move to validate a new tax and the priceunit of a downpayment
        res = super(AccountMove, self).action_post()
        line_ids = self.mapped('line_ids').filtered(lambda line: any(line.sale_line_ids.mapped('is_downpayment')))
        for line in line_ids:
            try:
                line.sale_line_ids.tax_id = line.tax_ids
                line.sale_line_ids.price_unit = line.price_unit
            except UserError:
                # a UserError here means the SO was locked, which prevents changing the taxes
                # just ignore the error - this is a nice to have feature and should not be blocking
                pass
        return res

    def _post(self, soft=True):
        # OVERRIDE
        # Auto-reconcile the invoice with payments coming from transactions.
        # It's useful when you have a "paid" sale order (using a payment transaction) and you invoice it later.
        posted = super()._post(soft)

        for invoice in posted.filtered(lambda move: move.is_invoice()):
            payments = invoice.mapped('transaction_ids.payment_id').filtered(lambda x: x.state == 'posted')
            move_lines = payments.line_ids.filtered(lambda line: line.account_internal_type in ('receivable', 'payable') and not line.reconciled)
            for line in move_lines:
                invoice.js_assign_outstanding_line(line.id)
        return posted

    def action_invoice_paid(self):
        # OVERRIDE
        res = super(AccountMove, self).action_invoice_paid()
        todo = set()
        for invoice in self.filtered(lambda move: move.is_invoice()):
            for line in invoice.invoice_line_ids:
                for sale_line in line.sale_line_ids:
                    todo.add((sale_line.order_id, invoice.name))
        for (order, name) in todo:
            order.message_post(body=_("Invoice %s paid", name))
        return res

    def _get_invoice_delivery_partner_id(self):
        # OVERRIDE
        self.ensure_one()
        return self.partner_shipping_id.id or super(AccountMove, self)._get_invoice_delivery_partner_id()

    def _action_invoice_ready_to_be_sent(self):
        # OVERRIDE
        # Make sure the send invoice CRON is called when an invoice becomes ready to be sent by mail.
        res = super()._action_invoice_ready_to_be_sent()

        send_invoice_cron = self.env.ref('sale.send_invoice_cron', raise_if_not_found=False)
        if send_invoice_cron:
            send_invoice_cron._trigger()

        return res

    def _is_downpayment(self):
        # OVERRIDE
        self.ensure_one()
        return self.line_ids.sale_line_ids and all(sale_line.is_downpayment for sale_line in self.line_ids.sale_line_ids) or False
