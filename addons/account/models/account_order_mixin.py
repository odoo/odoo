# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, _, api, fields, models
from odoo.tools import float_is_zero


class AccountOrderMixin(models.AbstractModel):
    # This mixin contains the shared logic between sale orders and purchase orders (ex. taxes, down payments, ...)
    _name = 'account.order.mixin'
    _description = 'Account Order Mixin'

    amount_to_invoice = fields.Monetary("Amount to invoice", compute='_compute_amount_to_invoice')
    amount_invoiced = fields.Monetary("Amount already invoiced", compute='_compute_amount_invoiced')

    # To override
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.company.currency_id.id)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', check_company=True)
    partner_id = fields.Many2one('res.partner', required=True, change_default=True, tracking=True, index=True, domain="[('company_id', 'in', (False, company_id))]")

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, compute='_compute_amounts')
    amount_tax = fields.Monetary(string="Taxes", store=True, compute='_compute_amounts')
    amount_total = fields.Monetary(string='Total', store=True, compute='_compute_amounts')

    account_move_ids = fields.Many2many('account.move')
    order_line = fields.One2many('account.order.line.mixin')

    invoice_status = fields.Selection([], compute='_compute_invoice_status', store=True)
    name = fields.Char(string="Order Reference", required=True, copy=False, readonly=False, index='trigram', default=lambda self: _('New'))
    payment_term_id = fields.Many2one('account.payment.term', 'Payment Terms', check_company=True)

    @api.depends('account_move_ids.state', 'currency_id', 'amount_total')
    def _compute_amount_to_invoice(self):
        pass  # To override

    @api.depends('amount_total', 'amount_to_invoice')
    def _compute_amount_invoiced(self):
        for order in self:
            order.amount_invoiced = order.amount_total - order.amount_to_invoice

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total')
    def _compute_amounts(self):
        """Compute the total amounts of the order."""
        for order in self:
            order_lines = order.order_line.filtered(lambda l: not l.display_type)

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes(
                    [
                        line._convert_to_tax_base_line_dict()
                        for line in order_lines
                    ],
                    order.company_id,
                )
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                amount_tax = sum(order_lines.mapped('price_tax'))

            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_total = order.amount_untaxed + order.amount_tax

    def _compute_invoice_status(self):
        pass  # To override

    def _get_copiable_order_lines(self):
        """Returns the order lines that can be copied to a new order."""
        return self.order_line.filtered(lambda l: not l.is_downpayment)

    def copy_data(self, default=None):
        default = default or {}
        default_has_no_order_line = 'order_line' not in default
        default.setdefault('order_line', [])
        vals_list = super().copy_data(default=default)
        if default_has_no_order_line:
            for order, vals in zip(self, vals_list):
                vals['order_line'] = [
                    Command.create(line_vals)
                    for line_vals in order._get_copiable_order_lines().copy_data()
                ]
        return vals_list

    def action_view_invoice(self, invoices=False):
        """
        Returns the action to view the provided invoices.
        Used to display the created invoices after creation.
        """
        raise NotImplementedError  # To override

    def _get_order_direction(self):
        """
        Returns the sign (1 or -1) to indicate whether the order is related to selling or buying (respectively)
        to multiply with when calculating the amount to invoice and creating the invoice lines.
        """
        raise NotImplementedError  # To override

    def _is_locked(self):
        """
        Returns whether the order is locked.
        Used to decide which down payment lines to update the status of when posting a linked down payment invoice.
        """
        raise NotImplementedError  # To override

    def _create_new_order_line(self, values):
        """
        Returns the results of a call to create() on the subrecord (sale.order.line or purchase.order.line).
        Used to create the order lines of the correct type.
        """
        raise NotImplementedError  # To override

    def _prepare_account_move_values(self):
        """
        Prepare the dict of values to create the new invoice for this order.
        Used when generating the invoice from this account order.
        """
        self.ensure_one()
        return {
            'currency_id': self.currency_id.id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }

    def _create_invoices(self, grouped=False, final=False, date=None):
        """
        Create the invoices for this account order.
        """
        raise NotImplementedError  # To override

    def _get_lang(self):
        self.ensure_one()

        if self.partner_id.lang and not self.partner_id.is_public:
            return self.partner_id.lang

        return self.env.lang

    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""

        # Keep down payment lines separately, to put them together
        # at the end of the invoice, in a specific dedicated section.
        down_payment_lines = []
        invoiceable_lines = []
        pending_section = None
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        for line in self.order_line:
            if line.display_type == 'line_section':
                # Only invoice the section if one of its lines is invoiceable
                pending_section = line
                continue
            if line.display_type != 'line_note' and float_is_zero(line.qty_to_invoice, precision_digits=precision):
                continue
            if line._has_valid_qty_to_invoice(final) or line.display_type == 'line_note':
                if line.is_downpayment:
                    down_payment_lines.append(line)
                    continue
                if pending_section:
                    invoiceable_lines.append(pending_section)
                    pending_section = None
                invoiceable_lines.append(line)

        return invoiceable_lines + down_payment_lines

    def _prepare_down_payment_section_line(self, **optional_values):
        """ Prepare the values to create a new down payment section.

        :param dict optional_values: any parameter that should be added to the returned down payment section
        :return: `account.move.line` creation values
        :rtype: dict
        """
        self.ensure_one()
        # Edit the context to properly translate the section heading (https://github.com/odoo/odoo/commit/964d35207717af9e7bf42e6f9293249cb6e48991)
        context = {'lang': self.partner_id.lang}
        down_payments_section_line = {
            'display_type': 'line_section',
            'name': _("Down Payments"),
            'product_id': False,
            'product_uom_id': False,
            'quantity': 0,
            'discount': 0,
            'price_unit': 0,
            'account_id': False,
            **optional_values
        }
        del context
        return down_payments_section_line

    def _get_order_lines_to_report(self):
        down_payment_lines = self.order_line.filtered(
            lambda line:
                line.is_downpayment
                and not line.display_type
                and not line._get_downpayment_state()
        )

        return self.order_line.filtered(
            lambda line:
                not line.is_downpayment
                or (line.display_type and down_payment_lines)
                or line in down_payment_lines
        )

    def _generate_invoice_values(self, final=False):
        invoice_vals_list = []
        sequence = 0
        for order in self:
            order = order.with_company(order.company_id).with_context(lang=order._get_lang())

            invoiceable_lines = order._get_invoiceable_lines(final)

            if not any(not line.display_type for line in invoiceable_lines):
                continue

            invoice_vals = order._prepare_account_move_values()
            invoice_line_vals = []
            down_payment_section_added = False
            for line in invoiceable_lines:
                if not down_payment_section_added and line.is_downpayment:
                    # Create a dedicated section for the down payments
                    # (put at the end of the invoiceable_lines, except for the initial down payment invoice itself)
                    invoice_line_vals.append(
                        Command.create(
                            order._prepare_down_payment_section_line(sequence=sequence)
                        ),
                    )
                    down_payment_section_added = True
                    sequence += 1
                invoice_line_vals.append(
                    Command.create(
                        line._prepare_invoice_line(sequence=sequence)
                    ),
                )
                sequence += 1

            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)
        return invoice_vals_list
