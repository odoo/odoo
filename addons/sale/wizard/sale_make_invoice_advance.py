# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import frozendict


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
        string="Down Payment",
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

    # UI
    display_draft_invoice_warning = fields.Boolean(compute="_compute_display_draft_invoice_warning")
    consolidated_billing = fields.Boolean(
        string="Consolidated Billing", default=True,
        help="Create one invoice for all orders related to same customer, same invoicing address"
             " and same delivery address."
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

    @api.depends('sale_order_ids')
    def _compute_display_draft_invoice_warning(self):
        for wizard in self:
            wizard.display_draft_invoice_warning = wizard.sale_order_ids.invoice_ids.filtered(lambda invoice: invoice.state == 'draft')

    @api.depends('sale_order_ids')
    def _compute_invoice_amounts(self):
        for wizard in self:
            wizard.amount_invoiced = sum(wizard.sale_order_ids._origin.mapped('amount_invoiced'))

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
            'view_mode': 'list',
            'views': [(False, 'list'), (False, 'form')],
            'res_model': 'account.move',
            'domain': [('line_ids.sale_line_ids.order_id', 'in', self.sale_order_ids.ids), ('state', '=', 'draft')],
        }

    #=== BUSINESS METHODS ===#

    def _prepare_down_payment_invoice_line_values(self, order, down_payment_base_line):
        self.ensure_one()

        context = {'lang': order.partner_id.lang}
        if self.advance_payment_method == 'percentage':
            name = _("Down payment of %s%%", self.amount)
        else:
            name = _("Down Payment")
        del context

        return down_payment_base_line['sale_line_ids'][0]._prepare_invoice_line(
            name=name,
            quantity=down_payment_base_line['quantity'],
            price_unit=down_payment_base_line['price_unit'],
            tax_ids=[Command.set(down_payment_base_line['tax_ids'].ids)],
            account_id=down_payment_base_line['account_id'].id,
            sale_line_ids=[Command.set(down_payment_base_line['sale_line_ids'].ids)],
            analytic_distribution=down_payment_base_line['analytic_distribution'],
            is_downpayment=True,
            extra_tax_data=self.env['account.tax']._export_base_line_extra_tax_data(down_payment_base_line),
        )

    def _prepare_down_payment_invoice_values(self, order, down_payment_base_lines):
        self.ensure_one()
        return {
            **order._prepare_invoice(),
            'invoice_line_ids': [
                Command.create(self._prepare_down_payment_invoice_line_values(order, base_line))
                for base_line in down_payment_base_lines
            ],
        }

    def _create_invoices(self, sale_orders):
        self.ensure_one()
        if self.advance_payment_method == 'delivered':
            return sale_orders._create_invoices(final=self.deduct_down_payments, grouped=not self.consolidated_billing)
        else:
            self.sale_order_ids.ensure_one()
            self = self.with_company(self.company_id)
            order = self.sale_order_ids

            AccountTax = self.env['account.tax']
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)

            if self.advance_payment_method == 'percentage':
                amount_type = 'percent'
                amount = self.amount
            else:  # self.advance_payment_method == 'fixed':
                amount_type = 'fixed'
                amount = self.fixed_amount

            def grouping_function(base_line):
                product_account = base_line['product_id'].product_tmpl_id.get_product_accounts(fiscal_pos=order.fiscal_position_id)
                account = product_account.get('downpayment') or product_account.get('income')
                return {'account_id': account}

            down_payment_base_lines = AccountTax._prepare_down_payment_lines(
                base_lines=base_lines,
                company=self.company_id,
                amount_type=amount_type,
                amount=amount,
                computation_key=f'down_payment,{self.id}',
                grouping_function=grouping_function,
            )

            # Update the sale order.
            order._add_down_payment_lines_from_base_lines(down_payment_base_lines)

            # Create the invoice.
            invoice_values = self._prepare_down_payment_invoice_values(order, down_payment_base_lines)
            invoice = self.env['account.move'].sudo().create(invoice_values)

            # Unsudo the invoice after creation if not already sudoed
            invoice = invoice.sudo(self.env.su)
            poster = self.env.user._is_internal() and self.env.user.id or SUPERUSER_ID
            invoice.with_user(poster).message_post_with_source(
                'mail.message_origin_link',
                render_values={'self': invoice, 'origin': order},
                subtype_xmlid='mail.mt_note',
            )

            title = _("Down payment invoice")
            order.with_user(poster).message_post(
                body=_("%s has been created", invoice._get_html_link(title=title)),
            )

            return invoice
