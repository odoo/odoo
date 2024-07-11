# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, api
from odoo.tools import format_date


class AccountOrderLineMixin(models.AbstractModel):
    # This mixin contains the shared logic between sale order lines and purchase order lines (ex. taxes, down payments, ...)
    _name = 'account.order.line.mixin'
    _description = 'Account Order Line Mixin'

    is_downpayment = fields.Boolean(
        string="Is a down payment",
        help="Down payments are made when creating account moves from an order. They are not copied when duplicating an order."
    )

    account_move_line_ids = fields.One2many('account.move.line')  # To override
    display_type = fields.Selection(
        [('line_section', "Section"), ('line_note', "Note")],
        help="Technical field for UX purpose.",
    )
    product_id = fields.Many2one('product.product', 'Product', change_default=True, index='btree_not_null')
    name = fields.Text(string='Description', compute='_compute_name', required=True, store=True, readonly=False, precompute=True)
    order_id = fields.Many2one('account.order.mixin')
    qty_to_invoice = fields.Float('Quantity to Invoice', compute='_compute_qty_to_invoice', digits='Product Unit of Measure', store=True)
    price_unit = fields.Float("Unit Price", digits='Product Price', compute='_compute_price_unit', required=True, readonly=False, store=True)
    tax_ids = fields.Many2many('account.tax', string="Taxes", check_company=True, context={'active_test': False})
    product_uom = fields.Many2one('uom.uom', "Unit of Measure", domain="[('category_id', '=', product_uom_category_id)]")
    discount = fields.Float("Discount (%)", digits='Discount', compute='_compute_discount', store=True, readonly=False, precompute=True)
    currency_id = fields.Many2one(related='order_id.currency_id', store=True, string='Currency', readonly=True, precompute=True)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)

    def _has_valid_qty_to_invoice(self, final=False):
        """
        Returns whether this account order line has a valid quantity for creating an invoice line from it.
        Used in account order to decide whether to create an invoice line for this entry.
        """
        raise NotImplementedError  # To override

    def _prepare_invoice_line(self, move=False, **optional_values):
        """
        Returns a dictionary of values to be used for creating the invoice line from this account order line.
        Used in account order to create the invoice lines.
        """
        self.ensure_one()
        return {
            'display_type': self.display_type or 'product',
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'discount': self.discount,
            'is_downpayment': self.is_downpayment,
        }

    def _get_invoice_lines(self):
        self.ensure_one()
        if self._context.get('accrual_entry_date'):
            return self.account_move_line_ids.filtered(
                lambda l: l.move_id.invoice_date and l.move_id.invoice_date <= self._context['accrual_entry_date']
            )
        else:
            return self.account_move_line_ids

    def _get_downpayment_state(self):
        self.ensure_one()

        if self.display_type:
            return None

        invoice_lines = self._get_invoice_lines()
        if all(line.parent_state == 'draft' for line in invoice_lines):
            return 'draft'
        if all(line.parent_state == 'cancel' for line in invoice_lines):
            return 'cancel'

        return None

    def _compute_name(self):
        for line in self:
            if line.is_downpayment:
                lang = line.order_id._get_lang()
                if lang != self.env.lang:
                    line = line.with_context(lang=lang)

                line.name = line._get_downpayment_description()

    @api.depends('price_unit', 'tax_ids', 'discount')
    def _compute_amount(self):
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes(
                [line._convert_to_tax_base_line_dict()],
                line.company_id,
            )
            totals = next(iter(tax_results['totals'].values()))
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']

            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })

    def _compute_price_unit(self):
        pass  # To override

    def _compute_discount(self):
        pass  # To override

    def _compute_qty_to_invoice(self):
        pass  # To override

    def _get_downpayment_description(self):
        self.ensure_one()
        if self.display_type:
            return _("Down Payments")

        dp_state = self._get_downpayment_state()
        name = _("Down Payment")
        if dp_state == 'draft':
            name = _(
                "Down Payment: %(date)s (Draft)",
                date=format_date(self.env, self.create_date.date()),
            )
        elif dp_state == 'cancel':
            name = _("Down Payment (Cancelled)")
        else:
            invoice = self._get_invoice_lines().filtered(
                lambda aml: aml.quantity >= 0
            ).move_id.filtered(lambda move: move.move_type in ['out_invoice', 'in_invoice'])
            if len(invoice) == 1 and invoice.payment_reference and invoice.invoice_date:
                name = _(
                    "Down Payment (ref: %(reference)s on %(date)s)",
                    reference=invoice.payment_reference,
                    date=format_date(self.env, invoice.invoice_date),
                )

        return name
