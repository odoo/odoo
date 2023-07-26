# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Command


class SaleAdvancePaymentInv(models.TransientModel):
    _name = 'sale.advance.payment.inv'
    _description = "Sales Advance Payment Invoice"

    advance_payment_method = fields.Selection(
        selection=[
            ('delivered', "Regular invoice"),
            ('percentage', "Down payment (percentage)"),
            ('fixed', "Down payment (fixed amount)"),
        ],
        string="Create Invoice",
        default='delivered',
        required=True,
        help="A standard invoice is issued with all the order lines ready for invoicing,"
            "according to their invoicing policy (based on ordered or delivered quantity).")
    count = fields.Integer(string="Order Count", compute='_compute_count')
    sale_order_ids = fields.Many2many(
        'sale.order', default=lambda self: self.env.context.get('active_ids'))

    # Down Payment logic
    has_down_payments = fields.Boolean(
        string="Has down payments", compute="_compute_has_down_payments")
    deduct_down_payments = fields.Boolean(string="Deduct down payments", default=True)

    # New Down Payment
    amount = fields.Float(
        string="Down Payment Amount",
        help="The percentage of amount to be invoiced in advance.")
    fixed_amount = fields.Monetary(
        string="Down Payment Amount (Fixed)",
        help="The fixed amount to be invoiced in advance.")
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency_id',
        store=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        compute='_compute_company_id',
        store=True)
    amount_invoiced = fields.Monetary(
        string="Already invoiced",
        compute="_compute_invoice_amounts",
        help="Only confirmed down payments are considered.")
    amount_to_invoice = fields.Monetary(
        string="Amount to invoice",
        compute="_compute_invoice_amounts",
        help="The amount to invoice = Sale Order Total - Confirmed Down Payments.")

    # UI
    display_draft_invoice_warning = fields.Boolean(compute="_compute_display_draft_invoice_warning")
    display_invoice_amount_warning = fields.Boolean(compute="_compute_display_invoice_amount_warning")
    consolidated_billing = fields.Boolean(
        string="Consolidated Billing", default=True,
        help="Create one invoice for all orders related to same customer and same invoicing address"
    )

    #=== COMPUTE METHODS ===#

    @api.depends('sale_order_ids')
    def _compute_count(self):
        for wizard in self:
            wizard.count = len(wizard.sale_order_ids)

    @api.depends('sale_order_ids')
    def _compute_has_down_payments(self):
        for wizard in self:
            wizard.has_down_payments = bool(
                wizard.sale_order_ids.order_line.filtered('is_downpayment')
            )

    # next computed fields are only used for down payments invoices and therefore should only
    # have a value when 1 unique SO is invoiced through the wizard
    @api.depends('sale_order_ids')
    def _compute_currency_id(self):
        self.currency_id = False
        for wizard in self:
            if wizard.count == 1:
                wizard.currency_id = wizard.sale_order_ids.currency_id

    @api.depends('sale_order_ids')
    def _compute_company_id(self):
        self.company_id = False
        for wizard in self:
            if wizard.count == 1:
                wizard.company_id = wizard.sale_order_ids.company_id

    @api.depends('amount', 'fixed_amount', 'advance_payment_method', 'amount_to_invoice')
    def _compute_display_invoice_amount_warning(self):
        for wizard in self:
            invoice_amount = wizard.fixed_amount
            if wizard.advance_payment_method == 'percentage':
                invoice_amount = wizard.amount / 100 * sum(wizard.sale_order_ids.mapped('amount_total'))
            wizard.display_invoice_amount_warning = invoice_amount > wizard.amount_to_invoice

    @api.depends('sale_order_ids')
    def _compute_display_draft_invoice_warning(self):
        for wizard in self:
            wizard.display_draft_invoice_warning = wizard.sale_order_ids.invoice_ids.filtered(lambda invoice: invoice.state == 'draft')

    @api.depends('sale_order_ids')
    def _compute_invoice_amounts(self):
        for wizard in self:
            wizard.amount_invoiced = sum(wizard.sale_order_ids._origin.mapped('amount_invoiced'))
            wizard.amount_to_invoice = sum(wizard.sale_order_ids._origin.mapped('amount_to_invoice'))

    #=== ONCHANGE METHODS ===#

    @api.onchange('advance_payment_method')
    def _onchange_advance_payment_method(self):
        if self.advance_payment_method == 'percentage':
            amount = self.default_get(['amount']).get('amount')
            return {'value': {'amount': amount}}

    #=== CONSTRAINT METHODS ===#

    def _check_amount_is_positive(self):
        for wizard in self:
            if wizard.advance_payment_method == 'percentage' and wizard.amount <= 0.00:
                raise UserError(_('The value of the down payment amount must be positive.'))
            elif wizard.advance_payment_method == 'fixed' and wizard.fixed_amount <= 0.00:
                raise UserError(_('The value of the down payment amount must be positive.'))


    #=== ACTION METHODS ===#

    def create_invoices(self):
        self._check_amount_is_positive()
        invoices = self._create_invoices(self.sale_order_ids)
        return self.sale_order_ids.action_view_invoice(invoices=invoices)

    def view_draft_invoices(self):
        return {
            'name': _('Draft Invoices'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'views': [(False, 'list'), (False, 'form')],
            'res_model': 'account.move',
            'domain': [('line_ids.sale_line_ids.order_id', 'in', self.sale_order_ids.ids), ('state', '=', 'draft')],
        }

    #=== BUSINESS METHODS ===#

    def _create_invoices(self, sale_orders):
        self.ensure_one()
        if self.advance_payment_method == 'delivered':
            return sale_orders._create_invoices(final=self.deduct_down_payments, grouped=not self.consolidated_billing)
        else:
            self.sale_order_ids.ensure_one()
            self = self.with_company(self.company_id)
            order = self.sale_order_ids


            # Create down payment section if necessary
            SaleOrderline = self.env['sale.order.line'].with_context(sale_no_log_for_new_lines=True)
            if not any(line.display_type and line.is_downpayment for line in order.order_line):
                SaleOrderline.create(
                    self._prepare_down_payment_section_values(order)
                )

            if self.advance_payment_method == 'percentage':
                ratio = self.amount / 100
            else:
                ratio = self.fixed_amount / order.amount_total if order.amount_total else 1

            values, accounts = order.get_down_payment_lines_values(ratio)
            down_payment_lines = SaleOrderline.create(values)

            invoice = self.env['account.move'].sudo().create(
                self._prepare_invoice_values(order, down_payment_lines, accounts)
            ).with_user(self.env.uid)  # Unsudo the invoice after creation

            # Ensure the invoice total is exactly the expected fixed amount.
            if self.advance_payment_method == 'fixed':
                delta_amount = (invoice.amount_total - self.fixed_amount) * (1 if invoice.is_inbound() else -1)
                invoice._ventilate_delta_amount(delta_amount)

            poster = self.env.user._is_internal() and self.env.user.id or SUPERUSER_ID
            invoice.with_user(poster).message_post_with_source(
                'mail.message_origin_link',
                render_values={'self': invoice, 'origin': order},
                subtype_xmlid='mail.mt_note',
            )

            order.with_user(poster).message_post(
                body=_("%s has been created",
                        invoice._get_html_link(title=_("Down payment invoice"))),
            )

            return invoice

    def _prepare_down_payment_section_values(self, order):
        context = {'lang': order.partner_id.lang}

        so_values = {
            'name': _('Down Payments'),
            'product_uom_qty': 0.0,
            'order_id': order.id,
            'display_type': 'line_section',
            'is_downpayment': True,
            'sequence': order.order_line and order.order_line[-1].sequence + 1 or 10,
        }

        del context
        return so_values

    # def _prepare_down_payment_lines_values(self, order):
    #     """ Create one down payment line per tax or unique taxes combination and per account.
    #         Apply the tax(es) to their respective lines.

    #         :param order: Order for which the down payment lines are created.
    #         :return:      An array containing an array of accounts at and an array of dicts with the
    #                       down payment lines values.
    #     """

    #     self.ensure_one()

    #     return order._get_down_payment_lines_values(ratio)

    # def _prepare_base_downpayment_line_values(self, order):
    #     order.ensure_one()
    #     context = {'lang': order.partner_id.lang}
    #     so_values = {
    #         'product_uom_qty': 0.0,
    #         'order_id': order.id,
    #         'discount': 0.0,
    #         'is_downpayment': True,
    #         'sequence': order.order_line and order.order_line[-1].sequence + 1 or 10,
    #     }
    #     del context
    #     return so_values

    def _prepare_invoice_values(self, order, so_lines, accounts):
        self.ensure_one()
        return {
            **order._prepare_invoice(),
            'invoice_line_ids': [Command.create(
                line._prepare_invoice_line(
                    name=self._get_down_payment_description(order),
                    quantity=1.0,
                    **({'account_id': account_id} if account_id else {}),
                )
            ) for line, account_id in zip(so_lines, accounts)],
        }

    def _get_down_payment_description(self, order):
        self.ensure_one()
        context = {'lang': order.partner_id.lang}
        if self.advance_payment_method == 'percentage':
            name = _("Down payment of %s%%", self.amount)
        else:
            name = _('Down Payment')
        del context
        return name
