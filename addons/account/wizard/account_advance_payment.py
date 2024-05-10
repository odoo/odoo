#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError
from odoo.tools import frozendict, float_compare


class AdvancePaymentWizard(models.AbstractModel):
    _name = 'account.advance.payment.wizard'
    _description = "Advance Payment Account Move"

    advance_payment_method = fields.Selection(
        selection=[
            ('delivered', "Regular invoice/bill"),
            ('percentage', "Down payment (percentage)"),
            ('fixed', "Down payment (fixed amount)"),
        ],
        string="Create Invoice",
        default='delivered',
        required=True,
        help="A standard invoice is issued with all the order lines ready for invoicing, "
             "according to their invoicing policy (based on ordered or delivered quantity).",
    )
    count = fields.Integer(string="Order Count", compute='_compute_count')
    order_ids = fields.Many2many('account.order.mixin', default=lambda self: self.env.context.get('active_ids'))

    # Down Payment logic
    has_down_payments = fields.Boolean(string="Has down payments", compute="_compute_has_down_payments")

    # New Down Payment
    amount = fields.Float(
        string="Down Payment",
        help="The percentage of amount to be invoiced in advance.",
    )
    fixed_amount = fields.Monetary(
        string="Down Payment Amount (Fixed)",
        help="The fixed amount to be invoiced in advance.",
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency_id',
        store=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        compute='_compute_company_id',
        store=True,
    )
    amount_invoiced = fields.Monetary(
        string="Already invoiced",
        compute="_compute_invoice_amounts",
        help="Only confirmed down payments and invoiced amounts are considered.",
    )
    amount_to_invoice = fields.Monetary(
        string="Amount to invoice",
        compute="_compute_invoice_amounts",
    )

    # UI
    display_draft_invoice_warning = fields.Boolean(compute="_compute_display_draft_invoice_warning")
    display_invoice_amount_warning = fields.Boolean(compute="_compute_display_invoice_amount_warning")

    # === HOOKS ===#
    def _needs_to_group_on_invoice(self):
        """
        Returns whether to create one invoice for all orders related to the same partner and invoicing address.
        Used for setting the grouped parameter on invoice creation.
        """
        return False

    def _get_payment_term_account_type(self):
        """
        Returns a string with the account_type to filter the account move lines on the created invoice.
        Used to check the rounding on the invoice lines after down payment invoice creation.
        """
        raise NotImplementedError  # To override

    def _get_product_account_internal_group(self):
        """
        Returns the account category (expense or income) to use for getting the correct account from the product.
        Used when creating the down payment lines.
        """
        raise NotImplementedError  # To override

    # === COMPUTE METHODS ===#

    @api.depends('order_ids')
    def _compute_count(self):
        for wizard in self:
            wizard.count = len(wizard.order_ids)

    @api.depends('order_ids')
    def _compute_has_down_payments(self):
        for wizard in self:
            wizard.has_down_payments = any(
                wizard.order_ids.order_line.mapped('is_downpayment')
            )

    # next computed fields are only used for down payments invoices and therefore should only
    # have a value when 1 unique order is invoiced through the wizard
    # =============

    @api.depends('order_ids')
    def _compute_currency_id(self):
        self.currency_id = False
        for wizard in self:
            if wizard.count == 1:
                wizard.currency_id = wizard.order_ids.currency_id

    @api.depends('order_ids')
    def _compute_company_id(self):
        self.company_id = False
        for wizard in self:
            if wizard.count == 1:
                wizard.company_id = wizard.order_ids.company_id

    # =============

    @api.depends('amount', 'fixed_amount', 'advance_payment_method', 'amount_to_invoice')
    def _compute_display_invoice_amount_warning(self):
        for wizard in self:
            invoice_amount = wizard.fixed_amount
            if wizard.advance_payment_method == 'percentage':
                invoice_amount = wizard.amount / 100 * sum(wizard.order_ids.mapped('amount_total'))
            wizard.display_invoice_amount_warning = invoice_amount > wizard.amount_to_invoice

    @api.depends('order_ids')
    def _compute_display_draft_invoice_warning(self):
        for wizard in self:
            wizard.display_draft_invoice_warning = any(invoice.state == 'draft' for invoice in wizard.order_ids.account_move_ids)

    @api.depends('order_ids')
    def _compute_invoice_amounts(self):
        for wizard in self:
            # _origin -> See https://github.com/odoo/odoo/pull/133836
            wizard.amount_invoiced = sum(wizard.order_ids._origin.mapped('amount_invoiced'))
            wizard.amount_to_invoice = sum(wizard.order_ids._origin.mapped('amount_to_invoice'))

    # === CONSTRAINT METHODS ===#

    def _check_amount_is_positive(self):
        for wizard in self:
            if (wizard.advance_payment_method == 'percentage' and float_compare(wizard.amount, 0, precision_rounding=wizard.currency_id.rounding) <= 0) \
                    or (wizard.advance_payment_method == 'fixed' and float_compare(wizard.fixed_amount, 0, precision_rounding=wizard.currency_id.rounding) <= 0):
                raise UserError(_('The value of a down payment amount must be positive.'))

    # === ACTION METHODS ===#

    def create_invoices(self):
        self._check_amount_is_positive()
        invoices = self._create_invoices(self.order_ids)
        return self.order_ids.action_view_invoice(invoices=invoices)

    def view_draft_invoices(self):
        return {
            'name': _('Draft Invoices'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'views': [(False, 'list'), (False, 'form')],
            'res_model': 'account.move',
            'domain': [('state', '=', 'draft')],  # To override
        }

    def _create_invoices(self, orders):
        if self.advance_payment_method == 'delivered':
            return orders._create_invoices(final=True, grouped=self._needs_to_group_on_invoice())

        return self._create_down_payment_invoice()

    def _create_down_payment_invoice(self):
        self.order_ids.ensure_one()
        self_c = self.with_company(self.company_id)
        order = self_c.order_ids

        # Create down payment section if necessary
        if not any(line.display_type and line.is_downpayment for line in order.order_line):
            self_c.order_ids.with_context(no_log_for_new_lines=True)._create_new_order_line(
                self_c._prepare_down_payment_section_values(order)
            )

        values, accounts = self_c._prepare_down_payment_lines_values(order)
        down_payment_lines = self_c.order_ids.with_context(no_log_for_new_lines=True)._create_new_order_line(values)

        invoice = self_c.env['account.move'].sudo().create(
            self_c._prepare_down_payment_invoice_values(order, down_payment_lines, accounts)
        )

        # Ensure the invoice total is exactly the expected fixed amount.
        if self_c.advance_payment_method == 'fixed':
            delta_amount = (invoice.amount_total - self_c.fixed_amount) * (-1 if invoice.is_inbound() else 1) * self_c.order_ids._get_order_direction()
            if not order.currency_id.is_zero(delta_amount):
                receivable_line = invoice.line_ids.filtered(lambda aml: aml.account_id.account_type == self_c._get_payment_term_account_type())[:1]
                product_lines = invoice.line_ids.filtered(lambda aml: aml.display_type == 'product')
                tax_lines = invoice.line_ids.filtered(lambda aml: aml.tax_line_id.amount_type not in (False, 'fixed'))

                if product_lines and tax_lines and receivable_line:
                    line_commands = [Command.update(receivable_line.id, {
                        'amount_currency': receivable_line.amount_currency + delta_amount,
                    })]
                    delta_sign = 1 if delta_amount > 0 else -1
                    for lines, attr, sign in (
                        (product_lines, 'price_total', -1),
                        (tax_lines, 'amount_currency', 1),
                    ):
                        remaining = delta_amount
                        for line in lines:
                            if order.currency_id.compare_amounts(remaining, 0) != delta_sign:
                                break
                            amt = delta_sign * max(
                                order.currency_id.rounding,
                                abs(order.currency_id.round(remaining / len(lines))),
                            )
                            remaining -= amt
                            line_commands.append(Command.update(line.id, {attr: line[attr] + amt * sign}))
                    invoice.line_ids = line_commands

        # Unsudo the invoice after creation if not already sudoed
        invoice = invoice.sudo(self_c.env.su)

        return invoice

    def _prepare_down_payment_section_values(self, order):
        return {
            'product_uom_qty': 0.0,
            'order_id': order.id,
            'display_type': 'line_section',
            'is_downpayment': True,
            'sequence': order.order_line and order.order_line[-1].sequence + 1 or 10,
        }

    def _prepare_down_payment_lines_values(self, order):
        """ Create one down payment line per tax or unique taxes combination and per account.
            Apply the tax(es) to their respective lines.

            :param order: Order for which the down payment lines are created.
            :return:      An array of dicts with the down payment lines values.
        """
        self.ensure_one()

        if self.advance_payment_method == 'percentage':
            ratio = self.amount / 100
        else:
            ratio = self.fixed_amount / order.amount_total if order.amount_total else 1

        order_lines = order.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)
        base_downpayment_lines_values = self._prepare_base_downpayment_line_values(order)

        tax_base_line_dicts = [
            line._convert_to_tax_base_line_dict(
                analytic_distribution=line.analytic_distribution,
                handle_price_include=False
            )
            for line in order_lines
        ]
        computed_taxes = self.env['account.tax']._compute_taxes(tax_base_line_dicts, self.company_id)
        down_payment_values = []
        for line, tax_repartition in computed_taxes['base_lines_to_update']:
            account = line['product'].product_tmpl_id.get_product_accounts(
                fiscal_pos=order.fiscal_position_id
            ).get(self._get_product_account_internal_group())
            taxes = line['taxes'].flatten_taxes_hierarchy()
            fixed_taxes = taxes.filtered(lambda tax: tax.amount_type == 'fixed')
            down_payment_values.append([
                taxes - fixed_taxes,
                line['analytic_distribution'],
                tax_repartition['price_subtotal'],
                account,
            ])
            for fixed_tax in fixed_taxes:
                # Fixed taxes cannot be set as taxes on down payments as they always amounts to 100%
                # of the tax amount. Therefore fixed taxes are removed and are replace by a new line
                # with appropriate amount, and non fixed taxes if the fixed tax affected the base of
                # any other non fixed tax.
                if fixed_tax.price_include:
                    continue

                if fixed_tax.include_base_amount:
                    pct_tax = taxes[list(taxes).index(fixed_tax) + 1:]\
                        .filtered(lambda t: t.is_base_affected and t.amount_type != 'fixed')
                else:
                    pct_tax = self.env['account.tax']
                down_payment_values.append([
                    pct_tax,
                    line['analytic_distribution'],
                    line['quantity'] * fixed_tax.amount,
                    account,
                ])

        downpayment_line_map = {}
        for tax_id, analytic_distribution, price_subtotal, account in down_payment_values:
            grouping_key = frozendict({
                'tax_ids': tuple(sorted(tax_id.ids)),
                'analytic_distribution': analytic_distribution,
                'account_id': account,
            })
            downpayment_line_map.setdefault(grouping_key, {
                **base_downpayment_lines_values,
                'tax_ids': grouping_key['tax_ids'],
                'analytic_distribution': grouping_key['analytic_distribution'],
                'product_uom_qty': 0.0,
                'price_unit': 0.0,
            })
            downpayment_line_map[grouping_key]['price_unit'] += price_subtotal
        for key in downpayment_line_map:
            downpayment_line_map[key]['price_unit'] = order.currency_id.round(downpayment_line_map[key]['price_unit'] * ratio)

        return list(downpayment_line_map.values()), [key['account_id'] for key in downpayment_line_map]

    def _prepare_base_downpayment_line_values(self, order):
        self.ensure_one()
        return {
            'product_uom_qty': 0.0,
            'order_id': order.id,
            'discount': 0.0,
            'is_downpayment': True,
            'sequence': order.order_line and order.order_line[-1].sequence + 1 or 10,
        }

    def _prepare_down_payment_invoice_values(self, order, dp_lines, accounts):
        self.ensure_one()
        return {
            **order._prepare_account_move_values(),
            'invoice_line_ids': [Command.create(
                line._prepare_invoice_line(
                    name=self._get_down_payment_description(order),
                    quantity=1.0,
                    **({'account_id': account.id} if account else {})
                )
            ) for line, account in zip(dp_lines, accounts)],
        }

    def _get_down_payment_description(self, order):
        self.ensure_one()
        context = {'lang': order.partner_id.lang}
        if self.advance_payment_method == 'percentage':
            name = _("Down payment of %(amount)s%%", amount=self.amount)
        else:
            name = _("Down Payment")
        del context
        return name
