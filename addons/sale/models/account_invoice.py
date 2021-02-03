# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _get_default_team(self):
        return self.env['crm.team']._get_default_team_id()

    def _default_comment(self):
        invoice_type = self.env.context.get('type', 'out_invoice')
        if invoice_type == 'out_invoice' and self.env['ir.config_parameter'].sudo().get_param('sale.use_sale_note'):
            return self.env.user.company_id.sale_note

    team_id = fields.Many2one('crm.team', string='Sales Team', default=_get_default_team, oldname='section_id')
    comment = fields.Text(default=_default_comment)
    partner_shipping_id = fields.Many2one(
        'res.partner',
        string='Delivery Address',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Delivery address for current invoice.")

    @api.onchange('partner_shipping_id', 'company_id')
    def _onchange_partner_shipping_id(self):
        """
        Trigger the change of fiscal position when the shipping address is modified.
        """
        fiscal_position = self.env['account.fiscal.position'].with_context(force_company=self.company_id.id).get_fiscal_position(self.partner_id.id, self.partner_shipping_id.id)
        if fiscal_position:
            self.fiscal_position_id = fiscal_position

    @api.multi
    def unlink(self):
        downpayment_lines = self.mapped('invoice_line_ids.sale_line_ids').filtered(lambda line: line.is_downpayment and line.invoice_lines <= self.mapped('invoice_line_ids'))
        res = super(AccountInvoice, self).unlink()
        if downpayment_lines:
            downpayment_lines.unlink()
        return res

    @api.onchange('partner_id', 'company_id')
    def _onchange_delivery_address(self):
        addr = self.partner_id.address_get(['delivery'])
        self.partner_shipping_id = addr and addr.get('delivery')
        inv_type = self.type or self.env.context.get('type', 'out_invoice')
        if inv_type == 'out_invoice':
            company = self.company_id or self.env.user.company_id
            self.comment = company.with_context(lang=self.partner_id.lang or self.env.lang).sale_note or (self._origin.company_id == company and self.comment)

    @api.multi
    def action_invoice_open(self):
        # OVERRIDE
        # Auto-reconcile the invoice with payments coming from transactions.
        # It's useful when you have a "paid" sale order (using a payment transaction) and you invoice it later.
        res = super(AccountInvoice, self).action_invoice_open()

        if not self:
            return res

        for invoice in self:
            payments = invoice.mapped('transaction_ids.payment_id')
            move_lines = payments.mapped('move_line_ids').filtered(lambda line: not line.reconciled and line.credit > 0.0)
            for line in move_lines:
                invoice.assign_outstanding_credit(line.id)
        return res

    @api.multi
    def action_invoice_paid(self):
        res = super(AccountInvoice, self).action_invoice_paid()
        todo = set()
        for invoice in self:
            for line in invoice.invoice_line_ids:
                for sale_line in line.sale_line_ids:
                    todo.add((sale_line.order_id, invoice.number))
        for (order, name) in todo:
            order.message_post(body=_("Invoice %s paid") % (name))
        return res

    @api.model
    def _refund_cleanup_lines(self, lines):
        result = super(AccountInvoice, self)._refund_cleanup_lines(lines)
        if self.env.context.get('mode') == 'modify':
            for i, line in enumerate(lines):
                for name, field in line._fields.items():
                    if name == 'sale_line_ids':
                        result[i][2][name] = [(6, 0, line[name].ids)]
                        line[name] = False
        return result

    @api.multi
    def get_delivery_partner_id(self):
        self.ensure_one()
        return self.partner_shipping_id.id or super(AccountInvoice, self).get_delivery_partner_id()

    def _get_refund_common_fields(self):
        return super(AccountInvoice, self)._get_refund_common_fields() + ['team_id', 'partner_shipping_id']

    def _get_intrastat_country_id(self):
        if self.type in ['out_invoice', 'out_refund']:
            return self.partner_shipping_id.country_id.id or super(AccountInvoice, self)._get_intrastat_country_id()
        return super(AccountInvoice, self)._get_intrastat_country_id()


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    _order = 'invoice_id, sequence, id'

    sale_line_ids = fields.Many2many(
        'sale.order.line',
        'sale_order_line_invoice_rel',
        'invoice_line_id', 'order_line_id',
        string='Sales Order Lines', readonly=True, copy=False)
