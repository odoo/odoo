# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero, format_date, groupby
from odoo.tools.translate import _


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = 'analytic.mixin'
    _description = "Sales Order Line"
    _rec_names_search = ['name', 'order_id.name']
    _order = 'order_id, sequence, id'
    _check_company_auto = True

    _sql_constraints = [
        ('accountable_required_fields',
            "CHECK(display_type IS NOT NULL OR is_downpayment OR (product_id IS NOT NULL AND product_uom IS NOT NULL))",
            "Missing required fields on accountable sale order line."),
        ('non_accountable_null_fields',
            "CHECK(display_type IS NULL OR (product_id IS NULL AND price_unit = 0 AND product_uom_qty = 0 AND product_uom IS NULL AND customer_lead = 0))",
            "Forbidden values on non-accountable sale order line"),
    ]

    # Fields are ordered according by tech & business logics
    # and computed fields are defined after their dependencies.
    # This reduces execution stacks depth when precomputing fields
    # on record creation (and is also a good ordering logic imho)

    order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Order Reference",
        required=True, ondelete='cascade', index=True, copy=False)
    sequence = fields.Integer(string="Sequence", default=10)

    # Order-related fields
    company_id = fields.Many2one(
        related='order_id.company_id',
        store=True, index=True, precompute=True)
    currency_id = fields.Many2one(
        related='order_id.currency_id',
        depends=['order_id.currency_id'],
        store=True, precompute=True)
    order_partner_id = fields.Many2one(
        related='order_id.partner_id',
        string="Customer",
        store=True, index=True, precompute=True)
    salesman_id = fields.Many2one(
        related='order_id.user_id',
        string="Salesperson",
        store=True, precompute=True)
    state = fields.Selection(
        related='order_id.state',
        string="Order Status",
        copy=False, store=True, precompute=True)
    tax_country_id = fields.Many2one(related='order_id.tax_country_id')

    # Fields specifying custom line logic
    display_type = fields.Selection(
        selection=[
            ('line_section', "Section"),
            ('line_note', "Note"),
        ],
        default=False)
    is_configurable_product = fields.Boolean(
        string="Is the product configurable?",
        related='product_template_id.has_configurable_attributes',
        depends=['product_template_id'])
    is_downpayment = fields.Boolean(
        string="Is a down payment",
        help="Down payments are made when creating invoices from a sales order."
            " They are not copied when duplicating a sales order.")
    is_expense = fields.Boolean(
        string="Is expense",
        help="Is true if the sales order line comes from an expense or a vendor bills")

    # Generic configuration fields
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        change_default=True, ondelete='restrict', index='btree_not_null',
        domain="[('sale_ok', '=', True)]")
    product_template_id = fields.Many2one(
        string="Product Template",
        comodel_name='product.template',
        compute='_compute_product_template_id',
        readonly=False,
        search='_search_product_template_id',
        # previously related='product_id.product_tmpl_id'
        # not anymore since the field must be considered editable for product configurator logic
        # without modifying the related product_id when updated.
        domain=[('sale_ok', '=', True)])
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', depends=['product_id'])

    product_template_attribute_value_ids = fields.Many2many(
        related='product_id.product_template_attribute_value_ids',
        depends=['product_id'])
    product_custom_attribute_value_ids = fields.One2many(
        comodel_name='product.attribute.custom.value', inverse_name='sale_order_line_id',
        string="Custom Values",
        compute='_compute_custom_attribute_values',
        store=True, readonly=False, precompute=True, copy=True)
    # M2M holding the values of product.attribute with create_variant field set to 'no_variant'
    # It allows keeping track of the extra_price associated to those attribute values and add them to the SO line description
    product_no_variant_attribute_value_ids = fields.Many2many(
        comodel_name='product.template.attribute.value',
        string="Extra Values",
        compute='_compute_no_variant_attribute_values',
        store=True, readonly=False, precompute=True, ondelete='restrict')
    is_product_archived = fields.Boolean(compute="_compute_is_product_archived")

    name = fields.Text(
        string="Description",
        compute='_compute_name',
        store=True, readonly=False, required=True, precompute=True)
    translated_product_name = fields.Text(compute='_compute_translated_product_name')

    product_uom_qty = fields.Float(
        string="Quantity",
        compute='_compute_product_uom_qty',
        digits='Product Unit of Measure', default=1.0,
        store=True, readonly=False, required=True, precompute=True)
    product_uom = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        compute='_compute_product_uom',
        store=True, readonly=False, precompute=True, ondelete='restrict',
        domain="[('category_id', '=', product_uom_category_id)]")
    linked_line_id = fields.Many2one(
        string="Linked Order Line",
        comodel_name='sale.order.line',
        ondelete='cascade',
        domain="[('order_id', '=', order_id)]",
        copy=False,
        index=True,
    )
    linked_line_ids = fields.One2many(
        string="Linked Order Lines", comodel_name='sale.order.line', inverse_name='linked_line_id',
    )
    # Uniquely identifies this sale order line before the record is saved in the DB, i.e. before the
    # record has an `id`.
    virtual_id = fields.Char()
    # Links this sale order line to another sale order line, via its `virtual_id`.
    linked_virtual_id = fields.Char()
    # Local storage of this sale order line's selected combo items, iff this is a combo product
    # line.
    selected_combo_items = fields.Char(store=False)
    combo_item_id = fields.Many2one(comodel_name='product.combo.item')

    # Pricing fields
    tax_id = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        compute='_compute_tax_id',
        store=True, readonly=False, precompute=True,
        context={'active_test': False},
        check_company=True)

    # Tech field caching pricelist rule used for price & discount computation
    pricelist_item_id = fields.Many2one(
        comodel_name='product.pricelist.item',
        compute='_compute_pricelist_item_id')

    price_unit = fields.Float(
        string="Unit Price",
        compute='_compute_price_unit',
        min_display_digits='Product Price',
        store=True, readonly=False, required=True, precompute=True)
    technical_price_unit = fields.Float()

    discount = fields.Float(
        string="Discount (%)",
        compute='_compute_discount',
        digits='Discount',
        store=True, readonly=False, precompute=True)

    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute='_compute_amount',
        store=True, precompute=True)
    price_tax = fields.Float(
        string="Total Tax",
        compute='_compute_amount',
        store=True, precompute=True)
    price_total = fields.Monetary(
        string="Total",
        compute='_compute_amount',
        store=True, precompute=True)
    price_reduce_taxexcl = fields.Monetary(
        string="Price Reduce Tax excl",
        compute='_compute_price_reduce_taxexcl',
        store=True, precompute=True)
    price_reduce_taxinc = fields.Monetary(
        string="Price Reduce Tax incl",
        compute='_compute_price_reduce_taxinc',
        store=True, precompute=True)

    # Logistics/Delivery fields
    product_packaging_id = fields.Many2one(
        comodel_name='product.packaging',
        string="Packaging",
        compute='_compute_product_packaging_id',
        store=True, readonly=False, precompute=True,
        domain="[('sales', '=', True), ('product_id','=',product_id)]",
        check_company=True)
    product_packaging_qty = fields.Float(
        string="Packaging Quantity",
        compute='_compute_product_packaging_qty',
        store=True, readonly=False, precompute=True)

    customer_lead = fields.Float(
        string="Lead Time",
        compute='_compute_customer_lead',
        store=True, readonly=False, required=True, precompute=True,
        help="Number of days between the order confirmation and the shipping of the products to the customer")

    qty_delivered_method = fields.Selection(
        selection=[
            ('manual', "Manual"),
            ('analytic', "Analytic From Expenses"),
        ],
        string="Method to update delivered qty",
        compute='_compute_qty_delivered_method',
        store=True, precompute=True,
        help="According to product configuration, the delivered quantity can be automatically computed by mechanism:\n"
             "  - Manual: the quantity is set manually on the line\n"
             "  - Analytic From expenses: the quantity is the quantity sum from posted expenses\n"
             "  - Timesheet: the quantity is the sum of hours recorded on tasks linked to this sale line\n"
             "  - Stock Moves: the quantity comes from confirmed pickings\n")
    qty_delivered = fields.Float(
        string="Delivery Quantity",
        compute='_compute_qty_delivered',
        default=0.0,
        digits='Product Unit of Measure',
        store=True, readonly=False, copy=False)

    # Analytic & Invoicing fields
    qty_invoiced = fields.Float(
        string="Invoiced Quantity",
        compute='_compute_qty_invoiced',
        digits='Product Unit of Measure',
        store=True)
    qty_invoiced_posted = fields.Float(
        string="Invoiced Quantity (posted)",
        compute='_compute_qty_invoiced_posted',
        digits='Product Unit of Measure')
    qty_to_invoice = fields.Float(
        string="Quantity To Invoice",
        compute='_compute_qty_to_invoice',
        digits='Product Unit of Measure',
        store=True)

    analytic_line_ids = fields.One2many(
        comodel_name='account.analytic.line', inverse_name='so_line',
        string="Analytic lines")

    invoice_lines = fields.Many2many(
        comodel_name='account.move.line',
        relation='sale_order_line_invoice_rel', column1='order_line_id', column2='invoice_line_id',
        string="Invoice Lines",
        copy=False)
    invoice_status = fields.Selection(
        selection=[
            ('upselling', "Upselling Opportunity"),
            ('invoiced', "Fully Invoiced"),
            ('to invoice', "To Invoice"),
            ('no', "Nothing to Invoice"),
        ],
        string="Invoice Status",
        compute='_compute_invoice_status',
        store=True)

    untaxed_amount_invoiced = fields.Monetary(
        string="Untaxed Invoiced Amount",
        compute='_compute_untaxed_amount_invoiced',
        store=True)
    amount_invoiced = fields.Monetary(
        string="Invoiced Amount",
        compute='_compute_amount_invoiced',
        compute_sudo=True,  # ensure same access as `untaxed_amount_invoiced`
    )
    untaxed_amount_to_invoice = fields.Monetary(
        string="Untaxed Amount To Invoice",
        compute='_compute_untaxed_amount_to_invoice',
        store=True)
    amount_to_invoice = fields.Monetary(
        string="Un-invoiced Balance",
        compute='_compute_amount_to_invoice',
        compute_sudo=True,  # ensure same access as `untaxed_amount_to_invoice`
    )

    # Technical computed fields for UX purposes (hide/make fields readonly, ...)
    product_type = fields.Selection(related='product_id.type', depends=['product_id'])
    service_tracking = fields.Selection(related='product_id.service_tracking', depends=['product_id'])
    product_updatable = fields.Boolean(
        string="Can Edit Product",
        compute='_compute_product_updatable')
    product_uom_readonly = fields.Boolean(
        compute='_compute_product_uom_readonly')
    tax_calculation_rounding_method = fields.Selection(
        related='company_id.tax_calculation_rounding_method',
        string='Tax calculation rounding method', readonly=True)
    company_price_include = fields.Selection(related="company_id.account_price_include")

    #=== COMPUTE METHODS ===#

    @api.depends('order_partner_id', 'order_id', 'product_id')
    def _compute_display_name(self):
        name_per_id = self._additional_name_per_id()
        for so_line in self.sudo():
            if so_line.order_partner_id.lang:
                so_line = so_line.with_context(lang=so_line.order_id._get_lang())
            if (product := so_line.product_id).display_name:
                default_name = so_line._get_sale_order_line_multiline_description_sale()
                if so_line.name == default_name:
                    description = product.display_name
                else:
                    parts = (so_line.name or "").split('\n', 2)
                    description = parts[1] if len(parts) > 1 and parts[1] else product.display_name
            else:
                description = (so_line.name or "").split('\n', 1)[0]
            name = f"{so_line.order_id.name} - {description}"
            additional_name = name_per_id.get(so_line.id)
            if additional_name:
                name = f'{name} {additional_name}'
            so_line.display_name = name

    @api.depends('product_id')
    def _compute_product_template_id(self):
        for line in self:
            line.product_template_id = line.product_id.product_tmpl_id

    def _search_product_template_id(self, operator, value):
        return [('product_id.product_tmpl_id', operator, value)]

    @api.depends('product_id')
    def _compute_is_product_archived(self):
        for line in self:
            line.is_product_archived = line.product_id and not line.product_id.active

    @api.depends('product_id')
    def _compute_custom_attribute_values(self):
        for line in self:
            if not line.product_id:
                line.product_custom_attribute_value_ids = False
                continue
            if not line.product_custom_attribute_value_ids:
                continue
            valid_values = line.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
            # remove the is_custom values that don't belong to this template
            for pacv in line.product_custom_attribute_value_ids:
                if pacv.custom_product_template_attribute_value_id not in valid_values:
                    line.product_custom_attribute_value_ids -= pacv

    @api.depends('product_id')
    def _compute_no_variant_attribute_values(self):
        for line in self:
            if not line.product_id:
                line.product_no_variant_attribute_value_ids = False
                continue
            if not line.product_no_variant_attribute_value_ids:
                continue
            valid_values = line.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
            # remove the no_variant attributes that don't belong to this template
            for ptav in line.product_no_variant_attribute_value_ids:
                if ptav._origin not in valid_values:
                    line.product_no_variant_attribute_value_ids -= ptav

    @api.depends('product_id', 'linked_line_id', 'linked_line_ids')
    def _compute_name(self):
        for line in self:
            if not line.product_id and not line.is_downpayment:
                continue

            lang = line.order_id._get_lang()
            if lang != self.env.lang:
                line = line.with_context(lang=lang)

            if line.product_id:
                line.name = line._get_sale_order_line_multiline_description_sale()
                continue

            if line.is_downpayment:
                line.name = line._get_downpayment_description()

    def _get_sale_order_line_multiline_description_sale(self):
        """ Compute a default multiline description for this sales order line.

        In most cases the product description is enough but sometimes we need to append information that only
        exists on the sale order line itself.
        e.g:
        - custom attributes and attributes that don't create variants, both introduced by the "product configurator"
        - in event_sale we need to know specifically the sales order line as well as the product to generate the name:
          the product is not sufficient because we also need to know the event_id and the event_ticket_id (both which belong to the sale order line).
        """
        self.ensure_one()
        description = (
            self.product_id.get_product_multiline_description_sale()
            + self._get_sale_order_line_multiline_description_variants()
        )
        if self.linked_line_id and not self.combo_item_id:
            description += "\n" + _("Option for: %s", self.linked_line_id.product_id.display_name)
        if self.linked_line_ids and self.product_type != 'combo':
            description += "\n" + "\n".join([
                _("Option: %s", linked_line.product_id.display_name)
                for linked_line in self.linked_line_ids
            ])
        return description

    def _get_sale_order_line_multiline_description_variants(self):
        """When using no_variant attributes or is_custom values, the product
        itself is not sufficient to create the description: we need to add
        information about those special attributes and values.

        :return: the description related to special variant attributes/values
        :rtype: string
        """
        no_variant_ptavs = self.product_no_variant_attribute_value_ids._origin.filtered(
            # Only describe the attributes where a choice was made by the customer
            lambda ptav: ptav.display_type == 'multi' or ptav.attribute_line_id.value_count > 1
        )
        if not self.product_custom_attribute_value_ids and not no_variant_ptavs:
            return ""

        name = "\n"

        custom_ptavs = self.product_custom_attribute_value_ids.custom_product_template_attribute_value_id
        multi_ptavs = no_variant_ptavs.filtered(lambda ptav: ptav.display_type == 'multi').sorted()

        # display the no_variant attributes, except those that are also
        # displayed by a custom (avoid duplicate description)
        for ptav in (no_variant_ptavs - multi_ptavs - custom_ptavs):
            name += "\n" + ptav.display_name

        # display the selected values per attribute on a single for a multi checkbox
        for pta, ptavs in groupby(multi_ptavs, lambda ptav: ptav.attribute_id):
            name += "\n" + _(
                "%(attribute)s: %(values)s",
                attribute=pta.name,
                values=", ".join(ptav.name for ptav in ptavs)
            )

        # Sort the values according to _order settings, because it doesn't work for virtual records in onchange
        sorted_custom_ptav = self.product_custom_attribute_value_ids.custom_product_template_attribute_value_id.sorted()
        for patv in sorted_custom_ptav:
            pacv = self.product_custom_attribute_value_ids.filtered(lambda pcav: pcav.custom_product_template_attribute_value_id == patv)
            name += "\n" + pacv.display_name

        return name

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
            ).move_id.filtered(lambda move: move.move_type == 'out_invoice')
            if len(invoice) == 1 and invoice.payment_reference and invoice.invoice_date:
                name = _(
                    "Down Payment (ref: %(reference)s on %(date)s)",
                    reference=invoice.payment_reference,
                    date=format_date(self.env, invoice.invoice_date),
                )

        return name

    @api.depends('product_id')
    def _compute_translated_product_name(self):
        for line in self:
            line.translated_product_name = line.product_id.with_context(
                lang=line.order_id._get_lang(),
            ).display_name

    @api.depends('display_type', 'product_id', 'product_packaging_qty')
    def _compute_product_uom_qty(self):
        for line in self:
            if line.display_type:
                line.product_uom_qty = 0.0
                continue

            if not line.product_packaging_id:
                continue
            packaging_uom = line.product_packaging_id.product_uom_id
            qty_per_packaging = line.product_packaging_id.qty
            product_uom_qty = packaging_uom._compute_quantity(
                line.product_packaging_qty * qty_per_packaging, line.product_uom)
            if float_compare(product_uom_qty, line.product_uom_qty, precision_rounding=line.product_uom.rounding) != 0:
                line.product_uom_qty = product_uom_qty

    @api.depends('product_id')
    def _compute_product_uom(self):
        for line in self:
            if not line.product_uom or (line.product_id.uom_id.id != line.product_uom.id):
                line.product_uom = line.product_id.uom_id

    @api.depends('product_id', 'company_id')
    def _compute_tax_id(self):
        lines_by_company = defaultdict(lambda: self.env['sale.order.line'])
        cached_taxes = {}
        for line in self:
            if line.product_type == 'combo':
                line.tax_id = False
                continue
            lines_by_company[line.company_id] += line
        for company, lines in lines_by_company.items():
            for line in lines.with_company(company):
                taxes = None
                if line.product_id:
                    taxes = line.product_id.taxes_id._filter_taxes_by_company(company)
                if not line.product_id or not taxes:
                    # Nothing to map
                    line.tax_id = False
                    continue
                fiscal_position = line.order_id.fiscal_position_id
                cache_key = (fiscal_position.id, company.id, tuple(taxes.ids))
                cache_key += line._get_custom_compute_tax_cache_key()
                if cache_key in cached_taxes:
                    result = cached_taxes[cache_key]
                else:
                    result = fiscal_position.map_tax(taxes)
                    cached_taxes[cache_key] = result
                # If company_id is set, always filter taxes by the company
                line.tax_id = result

    def _get_custom_compute_tax_cache_key(self):
        """Hook method to be able to set/get cached taxes while computing them"""
        return tuple()

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_pricelist_item_id(self):
        for line in self:
            if not line.product_id or line.display_type or not line.order_id.pricelist_id:
                line.pricelist_item_id = False
            else:
                line.pricelist_item_id = line.order_id.pricelist_id._get_product_rule(
                    line.product_id,
                    quantity=line.product_uom_qty or 1.0,
                    uom=line.product_uom,
                    date=line._get_order_date(),
                )

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        def has_manual_price(line):
            # `line.currency_id` can be False for NewId records
            currency = (
                line.currency_id
                or line.company_id.currency_id
                or line.env.company.currency_id
            )
            return currency.compare_amounts(line.technical_price_unit, line.price_unit)

        force_recompute = self.env.context.get('force_price_recomputation')
        for line in self:
            # Don't compute the price for deleted lines.
            if not line.order_id:
                continue
            # check if the price has been manually set or there is already invoiced amount.
            # if so, the price shouldn't change as it might have been manually edited.
            if (
                (not force_recompute and has_manual_price(line))
                or line.qty_invoiced > 0
                or (line.product_id.expense_policy == 'cost' and line.is_expense)
            ):
                continue
            line = line.with_context(sale_write_from_compute=True)
            if not line.product_uom or not line.product_id:
                line.price_unit = 0.0
                line.technical_price_unit = 0.0
            else:
                line._reset_price_unit()

    def _reset_price_unit(self):
        self.ensure_one()

        line = self.with_company(self.company_id)
        price = line._get_display_price()
        product_taxes = line.product_id.taxes_id._filter_taxes_by_company(line.company_id)
        price_unit = line.product_id._get_tax_included_unit_price_from_price(
            price,
            product_taxes=product_taxes,
            fiscal_position=line.order_id.fiscal_position_id,
        )
        line.update({
            'price_unit': price_unit,
            'technical_price_unit': price_unit,
        })

    def _get_order_date(self):
        self.ensure_one()
        return self.order_id.date_order

    def _get_display_price(self):
        """Compute the displayed unit price for a given line.

        Overridden in custom flows:
        * where the price is not specified by the pricelist
        * where the discount is not specified by the pricelist

        Note: self.ensure_one()
        """
        self.ensure_one()

        if self.product_type == 'combo':
            return 0  # The display price of a combo line should always be 0.
        if self.combo_item_id:
            return self._get_combo_item_display_price()
        return self._get_display_price_ignore_combo()

    def _get_display_price_ignore_combo(self):
        """ This helper method allows to compute the display price of a SOL, while ignoring combo
        logic.

        I.e. this method returns the display price of a SOL as if it were neither a combo line nor a
        combo item line.
        """
        self.ensure_one()

        pricelist_price = self._get_pricelist_price()

        if not self.pricelist_item_id._show_discount():
            # No pricelist rule found => no discount from pricelist
            return pricelist_price

        base_price = self._get_pricelist_price_before_discount()

        # negative discounts (= surcharge) are included in the display price
        return max(base_price, pricelist_price)

    def _get_pricelist_price(self):
        """Compute the price given by the pricelist for the given line information.

        :return: the product sales price in the order currency (without taxes)
        :rtype: float
        """
        self.ensure_one()
        self.product_id.ensure_one()

        price = self.pricelist_item_id._compute_price(
            product=self.product_id.with_context(**self._get_product_price_context()),
            quantity=self.product_uom_qty or 1.0,
            uom=self.product_uom,
            date=self._get_order_date(),
            currency=self.currency_id,
        )

        return price

    def _get_product_price_context(self):
        """Gives the context for product price computation.

        :return: additional context to consider extra prices from attributes in the base product price.
        :rtype: dict
        """
        self.ensure_one()
        return self.product_id._get_product_price_context(
            self.product_no_variant_attribute_value_ids,
        )

    def _get_pricelist_price_context(self):
        """DO NOT USE in new code, this contextual logic should be dropped or heavily refactored soon"""
        self.ensure_one()
        return {
            'pricelist': self.order_id.pricelist_id.id,
            'uom': self.product_uom.id,
            'quantity': self.product_uom_qty,
            'date': self._get_order_date(),
        }

    def _get_pricelist_price_before_discount(self):
        """Compute the price used as base for the pricelist price computation.

        :return: the product sales price in the order currency (without taxes)
        :rtype: float
        """
        self.ensure_one()
        self.product_id.ensure_one()

        return self.pricelist_item_id._compute_price_before_discount(
            product=self.product_id.with_context(**self._get_product_price_context()),
            quantity=self.product_uom_qty or 1.0,
            uom=self.product_uom,
            date=self._get_order_date(),
            currency=self.currency_id,
        )

    def _get_combo_item_display_price(self):
        """ Compute the display price of this SOL's combo item.

        A combo item's price is a fraction of its combo product's price (i.e. the product of type
        `combo` which is referenced in this SOL's linked line). It is independent of the combo
        item's product (i.e. the product referenced in this SOL). The combo's `base_price` will be
        used to prorate the price of this combo with respect to the other combos in the combo
        product.

        Note: this method will throw if this SOL has no combo item or no linked combo product.
        """
        self.ensure_one()

        # Compute the combo product's price.
        combo_line = self._get_linked_line()
        combo_product_price = combo_line._get_display_price_ignore_combo()
        # Compute the combos' base prices.
        combo_base_prices = {
            combo_id: combo_id.currency_id._convert(
                from_amount=combo_id.base_price,
                to_currency=self.currency_id,
                company=self.company_id,
                date=self.order_id.date_order,
            ) for combo_id in combo_line.product_template_id.combo_ids
        }
        total_combo_base_price = sum(combo_base_prices.values())
        # Compute the prorated combo prices.
        combo_prices = {
            combo_id: self.currency_id.round(
                # Don't divide by total_combo_base_price if it's 0. This will make the prorating
                # wrong, but the delta will be fixed by combo_price_delta below.
                base_price * combo_product_price / (total_combo_base_price or 1)
            )
            for (combo_id, base_price) in combo_base_prices.items()
        }
        # Compute the delta between the combo product's price and the sum of its combo prices.
        # Ideally, this should be 0, but division in python isn't perfect, so we may need to adjust
        # the combo prices to make the delta 0.
        combo_price_delta = combo_product_price - sum(combo_prices.values())
        if combo_price_delta:
            combo_prices[combo_line.product_template_id.combo_ids[-1]] += combo_price_delta
        # Add the extra price of this combo item, as well as the extra prices of any `no_variant`
        # attributes to the combo price.
        return (
            combo_prices[self.combo_item_id.combo_id]
            + self.combo_item_id.extra_price
            + self.product_id._get_no_variant_attributes_price_extra(
                self.product_no_variant_attribute_value_ids
            )
        )

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_discount(self):
        discount_enabled = self.env['product.pricelist.item']._is_discount_feature_enabled()
        for line in self:
            if not line.product_id or line.display_type:
                line.discount = 0.0

            if not (line.order_id.pricelist_id and discount_enabled):
                continue

            if line.combo_item_id:
                line.discount = line._get_linked_line().discount
                continue

            line.discount = 0.0

            if not line.pricelist_item_id._show_discount():
                # No pricelist rule was found for the product
                # therefore, the pricelist didn't apply any discount/change
                # to the existing sales price.
                continue

            line = line.with_company(line.company_id)
            pricelist_price = line._get_pricelist_price()
            base_price = line._get_pricelist_price_before_discount()

            if base_price != 0:  # Avoid division by zero
                discount = (base_price - pricelist_price) / base_price * 100
                if (discount > 0 and base_price > 0) or (discount < 0 and base_price < 0):
                    # only show negative discounts if price is negative
                    # otherwise it's a surcharge which shouldn't be shown to the customer
                    line.discount = discount

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            **{
                'tax_ids': self.tax_id,
                'quantity': self.product_uom_qty,
                'partner_id': self.order_id.partner_id,
                'currency_id': self.order_id.currency_id or self.order_id.company_id.currency_id,
                'rate': self.order_id.currency_rate,
                **kwargs,
            },
        )

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        for line in self:
            base_line = line._prepare_base_line_for_taxes_computation()
            self.env['account.tax']._add_tax_details_in_base_line(base_line, line.company_id)
            line.price_subtotal = base_line['tax_details']['raw_total_excluded_currency']
            line.price_total = base_line['tax_details']['raw_total_included_currency']
            line.price_tax = line.price_total - line.price_subtotal

    @api.depends('price_subtotal', 'product_uom_qty')
    def _compute_price_reduce_taxexcl(self):
        for line in self:
            line.price_reduce_taxexcl = line.price_subtotal / line.product_uom_qty if line.product_uom_qty else 0.0

    @api.depends('price_total', 'product_uom_qty')
    def _compute_price_reduce_taxinc(self):
        for line in self:
            line.price_reduce_taxinc = line.price_total / line.product_uom_qty if line.product_uom_qty else 0.0

    @api.depends('product_id', 'product_uom_qty', 'product_uom')
    def _compute_product_packaging_id(self):
        for line in self:
            # remove packaging if not match the product
            if line.product_packaging_id.product_id != line.product_id:
                line.product_packaging_id = False
            # suggest biggest suitable packaging matching the SO's company
            if line.product_id and line.product_uom_qty and line.product_uom:
                suggested_packaging = line.product_id.packaging_ids\
                        .filtered(lambda p: p.sales and (p.product_id.company_id <= p.company_id <= line.company_id))\
                        ._find_suitable_product_packaging(line.product_uom_qty, line.product_uom)
                line.product_packaging_id = suggested_packaging or line.product_packaging_id

    @api.depends('product_packaging_id', 'product_uom', 'product_uom_qty')
    def _compute_product_packaging_qty(self):
        self.product_packaging_qty = 0
        for line in self:
            if not line.product_packaging_id:
                continue
            line.product_packaging_qty = line.product_packaging_id._compute_qty(line.product_uom_qty, line.product_uom)

    # This computed default is necessary to have a clean computation inheritance
    # (cf sale_stock) instead of simply removing the default and specifying
    # the compute attribute & method in sale_stock.
    def _compute_customer_lead(self):
        self.customer_lead = 0.0

    @api.depends('is_expense')
    def _compute_qty_delivered_method(self):
        """ Sale module compute delivered qty for product [('type', 'in', ['consu']), ('service_type', '=', 'manual')]
                - consu + expense_policy : analytic (sum of analytic unit_amount)
                - consu + no expense_policy : manual (set manually on SOL)
                - service (+ service_type='manual', the only available option) : manual

            This is true when only sale is installed: sale_stock redifine the behavior for 'consu' type,
            and sale_timesheet implements the behavior of 'service' + service_type=timesheet.
        """
        for line in self:
            if line.is_expense:
                line.qty_delivered_method = 'analytic'
            else:  # service and consu
                line.qty_delivered_method = 'manual'

    @api.depends(
        'qty_delivered_method',
        'analytic_line_ids.so_line',
        'analytic_line_ids.unit_amount',
        'analytic_line_ids.product_uom_id')
    def _compute_qty_delivered(self):
        """ This method compute the delivered quantity of the SO lines: it covers the case provide by sale module, aka
            expense/vendor bills (sum of unit_amount of AAL), and manual case.
            This method should be overridden to provide other way to automatically compute delivered qty. Overrides should
            take their concerned so lines, compute and set the `qty_delivered` field, and call super with the remaining
            records.
        """
        # compute for analytic lines
        lines_by_analytic = self.filtered(lambda sol: sol.qty_delivered_method == 'analytic')
        mapping = lines_by_analytic._get_delivered_quantity_by_analytic([('amount', '<=', 0.0)])
        for so_line in lines_by_analytic:
            so_line.qty_delivered = mapping.get(so_line.id or so_line._origin.id, 0.0)

    def _get_downpayment_state(self):
        self.ensure_one()

        if self.display_type:
            return ''

        invoice_lines = self._get_invoice_lines()
        if all(line.parent_state == 'draft' for line in invoice_lines):
            return 'draft'
        if all(line.parent_state == 'cancel' for line in invoice_lines):
            return 'cancel'

        return ''

    def _get_delivered_quantity_by_analytic(self, additional_domain):
        """ Compute and write the delivered quantity of current SO lines, based on their related
            analytic lines.
            :param additional_domain: domain to restrict AAL to include in computation (required since timesheet is an AAL with a project ...)
        """
        result = defaultdict(float)

        # avoid recomputation if no SO lines concerned
        if not self:
            return result

        # group analytic lines by product uom and so line
        domain = expression.AND([[('so_line', 'in', self.ids)], additional_domain])
        data = self.env['account.analytic.line']._read_group(
            domain,
            ['product_uom_id', 'so_line'],
            ['unit_amount:sum', 'move_line_id:count_distinct', '__count'],
        )

        # convert uom and sum all unit_amount of analytic lines to get the delivered qty of SO lines
        for uom, so_line, unit_amount_sum, move_line_id_count_distinct, count in data:
            if not uom:
                continue
            # avoid counting unit_amount twice when dealing with multiple analytic lines on the same move line
            if move_line_id_count_distinct == 1 and count > 1:
                qty = unit_amount_sum / count
            else:
                qty = unit_amount_sum
            if so_line.product_uom.category_id == uom.category_id:
                qty = uom._compute_quantity(qty, so_line.product_uom, rounding_method='HALF-UP')
            result[so_line.id] += qty

        return result

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity')
    def _compute_qty_invoiced(self):
        """
        Compute the quantity invoiced. If case of a refund, the quantity invoiced is decreased. Note
        that this is the case only if the refund is generated from the SO and that is intentional: if
        a refund made would automatically decrease the invoiced quantity, then there is a risk of reinvoicing
        it automatically, which may not be wanted at all. That's why the refund has to be created from the SO
        """
        for line in self:
            qty_invoiced = 0.0
            for invoice_line in line._get_invoice_lines():
                if invoice_line.move_id.state != 'cancel' or invoice_line.move_id.payment_state == 'invoicing_legacy':
                    if invoice_line.move_id.move_type == 'out_invoice':
                        qty_invoiced += invoice_line.product_uom_id._compute_quantity(invoice_line.quantity, line.product_uom, round=False)
                    elif invoice_line.move_id.move_type == 'out_refund':
                        qty_invoiced -= invoice_line.product_uom_id._compute_quantity(invoice_line.quantity, line.product_uom, round=False)
            line.qty_invoiced = qty_invoiced

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity')
    def _compute_qty_invoiced_posted(self):
        """
        This method is almost identical to '_compute_qty_invoiced()'. The only difference lies in the fact that
        for accounting purposes, we only want the quantities of the posted invoices.
        We need a dedicated computation because the triggers are different and could lead to incorrect values for
        'qty_invoiced' when computed together.
        """
        for line in self:
            qty_invoiced_posted = 0.0
            for invoice_line in line._get_invoice_lines():
                if invoice_line.move_id.state == 'posted' or invoice_line.move_id.payment_state == 'invoicing_legacy':
                    qty_unsigned = invoice_line.product_uom_id._compute_quantity(invoice_line.quantity, line.product_uom)
                    qty_signed = qty_unsigned * -invoice_line.move_id.direction_sign
                    qty_invoiced_posted += qty_signed
            line.qty_invoiced_posted = qty_invoiced_posted

    def _get_invoice_lines(self):
        self.ensure_one()
        if self._context.get('accrual_entry_date'):
            return self.invoice_lines.filtered(
                lambda l: l.move_id.invoice_date and l.move_id.invoice_date <= self._context['accrual_entry_date']
            )
        else:
            return self.invoice_lines

    # no trigger product_id.invoice_policy to avoid retroactively changing SO
    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'state')
    def _compute_qty_to_invoice(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        For combo product lines, compute the value if a linked combo item line gets recomputed,
        and set `qty_to_invoice` only if at least one of its combo item lines is invoiceable.
        """
        combo_lines = set()
        for line in self:
            if line.state == 'sale' and not line.display_type:
                if line.product_id.type == 'combo':
                    combo_lines.add(line)
                elif line.product_id.invoice_policy == 'order':
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
                if line.combo_item_id and line.linked_line_id:
                    combo_lines.add(line.linked_line_id)
            else:
                line.qty_to_invoice = 0
        for combo_line in combo_lines:
            if any(
                line.combo_item_id and line.qty_to_invoice
                for line in combo_line.linked_line_ids
            ):
                combo_line.qty_to_invoice = combo_line.product_uom_qty - combo_line.qty_invoiced
            else:
                combo_line.qty_to_invoice = 0

    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced')
    def _compute_invoice_status(self):
        """
        Compute the invoice status of a SO line. Possible statuses:
        - no: if the SO is not in status 'sale', we consider that there is nothing to
          invoice. This is also the default value if the conditions of no other status is met.
        - to invoice: we refer to the quantity to invoice of the line. Refer to method
          `_compute_qty_to_invoice()` for more information on how this quantity is calculated.
        - upselling: this is possible only for a product invoiced on ordered quantities for which
          we delivered more than expected. The could arise if, for example, a project took more
          time than expected but we decided not to invoice the extra cost to the client. This
          occurs only in state 'sale', the upselling opportunity is removed from the list.
        - invoiced: the quantity invoiced is larger or equal to the quantity ordered.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            if line.state != 'sale':
                line.invoice_status = 'no'
            elif line.is_downpayment and line.untaxed_amount_to_invoice == 0:
                line.invoice_status = 'invoiced'
            elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                line.invoice_status = 'to invoice'
            elif line.state == 'sale' and line.product_id.invoice_policy == 'order' and\
                    line.product_uom_qty >= 0.0 and\
                    float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1:
                line.invoice_status = 'upselling'
            elif float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) >= 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'

    def _can_be_invoiced_alone(self):
        """ Whether a given line is meaningful to invoice alone.

        It is generally meaningless/confusing or even wrong to invoice some specific SOlines
        (delivery, discounts, rewards, ...) without others, unless they are the only left to invoice
        in the SO.
        """
        self.ensure_one()
        return self.product_id.id != self.company_id.sale_discount_product_id.id

    def _is_discount_line(self):
        self.ensure_one()
        return self.product_id in self.company_id.sale_discount_product_id

    @api.depends('invoice_lines', 'invoice_lines.price_total', 'invoice_lines.move_id.state', 'invoice_lines.move_id.move_type')
    def _compute_untaxed_amount_invoiced(self):
        """ Compute the untaxed amount already invoiced from the sale order line, taking the refund attached
            the so line into account. This amount is computed as
                SUM(inv_line.price_subtotal) - SUM(ref_line.price_subtotal)
            where
                `inv_line` is a customer invoice line linked to the SO line
                `ref_line` is a customer credit note (refund) line linked to the SO line
        """
        for line in self:
            amount_invoiced = 0.0
            for invoice_line in line._get_invoice_lines():
                if invoice_line.move_id.state == 'posted' or invoice_line.move_id.payment_state == 'invoicing_legacy':
                    invoice_date = invoice_line.move_id.invoice_date or fields.Date.today()
                    if invoice_line.move_id.move_type == 'out_invoice':
                        amount_invoiced += invoice_line.currency_id._convert(invoice_line.price_subtotal, line.currency_id, line.company_id, invoice_date)
                    elif invoice_line.move_id.move_type == 'out_refund':
                        amount_invoiced -= invoice_line.currency_id._convert(invoice_line.price_subtotal, line.currency_id, line.company_id, invoice_date)
            line.untaxed_amount_invoiced = amount_invoiced

    @api.depends('invoice_lines', 'invoice_lines.price_total', 'invoice_lines.move_id.state')
    def _compute_amount_invoiced(self):
        for line in self:
            amount_invoiced = 0.0
            for invoice_line in line._get_invoice_lines():
                invoice = invoice_line.move_id
                if invoice.state == 'posted' or invoice_line.move_id.payment_state == 'invoicing_legacy':
                    invoice_date = invoice.invoice_date or fields.Date.context_today(self)
                    amount_invoiced_unsigned = invoice_line.currency_id._convert(invoice_line.price_total, line.currency_id, line.company_id, invoice_date)
                    amount_invoiced += amount_invoiced_unsigned * -invoice.direction_sign
            line.amount_invoiced = amount_invoiced

    @api.depends('state', 'product_id', 'untaxed_amount_invoiced', 'qty_delivered', 'product_uom_qty', 'price_unit')
    def _compute_untaxed_amount_to_invoice(self):
        """ Total of remaining amount to invoice on the sale order line (taxes excl.) as
                total_sol - amount already invoiced
            where Total_sol depends on the invoice policy of the product.

            Note: Draft invoice are ignored on purpose, the 'to invoice' amount should
            come only from the SO lines.
        """
        for line in self:
            amount_to_invoice = 0.0
            if line.state == 'sale':
                # Note: do not use price_subtotal field as it returns zero when the ordered quantity is
                # zero. It causes problem for expense line (e.i.: ordered qty = 0, deli qty = 4,
                # price_unit = 20 ; subtotal is zero), but when you can invoice the line, you see an
                # amount and not zero. Since we compute untaxed amount, we can use directly the price
                # reduce (to include discount) without using `compute_all()` method on taxes.
                price_subtotal = 0.0
                uom_qty_to_consider = line.qty_delivered if line.product_id.invoice_policy == 'delivery' else line.product_uom_qty
                price_reduce = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                price_subtotal = price_reduce * uom_qty_to_consider
                if len(line.tax_id.filtered(lambda tax: tax.price_include)) > 0:
                    # As included taxes are not excluded from the computed subtotal, `compute_all()` method
                    # has to be called to retrieve the subtotal without them.
                    # `price_reduce_taxexcl` cannot be used as it is computed from `price_subtotal` field. (see upper Note)
                    price_subtotal = line.tax_id.compute_all(
                        price_reduce,
                        currency=line.currency_id,
                        quantity=uom_qty_to_consider,
                        product=line.product_id,
                        partner=line.order_id.partner_shipping_id)['total_excluded']
                inv_lines = line._get_invoice_lines()
                if any(inv_lines.mapped(lambda l: l.discount != line.discount)):
                    # In case of re-invoicing with different discount we try to calculate manually the
                    # remaining amount to invoice
                    amount = 0
                    for l in inv_lines:
                        if len(l.tax_ids.filtered(lambda tax: tax.price_include)) > 0:
                            amount += l.tax_ids.compute_all(l.currency_id._convert(l.price_unit, line.currency_id, line.company_id, l.date or fields.Date.today(), round=False) * l.quantity)['total_excluded']
                        else:
                            amount += l.currency_id._convert(l.price_unit, line.currency_id, line.company_id, l.date or fields.Date.today(), round=False) * l.quantity

                    amount_to_invoice = max(price_subtotal - amount, 0)
                else:
                    amount_to_invoice = price_subtotal - line.untaxed_amount_invoiced

            line.untaxed_amount_to_invoice = amount_to_invoice

    @api.depends('discount', 'price_total', 'product_uom_qty', 'qty_delivered', 'qty_invoiced_posted')
    def _compute_amount_to_invoice(self):
        for line in self:
            if line.product_uom_qty:
                uom_qty_to_consider = line.qty_delivered if line.product_id.invoice_policy == 'delivery' else line.product_uom_qty
                qty_to_invoice = uom_qty_to_consider - line.qty_invoiced_posted
                unit_price_total = line.price_total / line.product_uom_qty
                line.amount_to_invoice = unit_price_total * qty_to_invoice
            else:
                line.amount_to_invoice = 0.0

    @api.depends('order_id.partner_id', 'product_id')
    def _compute_analytic_distribution(self):
        for line in self:
            if not line.display_type:
                distribution = line.env['account.analytic.distribution.model']._get_distribution({
                    "product_id": line.product_id.id,
                    "product_categ_id": line.product_id.categ_id.id,
                    "partner_id": line.order_id.partner_id.id,
                    "partner_category_id": line.order_id.partner_id.category_id.ids,
                    "company_id": line.company_id.id,
                })
                line.analytic_distribution = distribution or line.analytic_distribution

    @api.depends('product_id', 'state', 'qty_invoiced', 'qty_delivered')
    def _compute_product_updatable(self):
        self.product_updatable = True
        for line in self:
            if (
                line.is_downpayment
                or line.state == 'cancel'
                or line.state == 'sale' and (
                    line.order_id.locked
                    or line.qty_invoiced > 0
                    or line.qty_delivered > 0
                )
            ):
                line.product_updatable = False

    @api.depends('state')
    def _compute_product_uom_readonly(self):
        for line in self:
            # line.ids checks whether it's a new record not yet saved
            line.product_uom_readonly = line.ids and line.state in ['sale', 'cancel']

    #=== CONSTRAINT METHODS ===#

    @api.constrains('combo_item_id')
    def _check_combo_item_id(self):
        """ `combo_item_id` should never be set manually. This constraint mainly serves to avoid
        programming errors.
        """
        for line in self:
            linked_line = line._get_linked_line()
            allowed_combo_items = linked_line.product_template_id.combo_ids.combo_item_ids
            if line.combo_item_id and line.combo_item_id not in allowed_combo_items:
                raise ValidationError(_(
                    "A sale order line's combo item must be among its linked line's available"
                    " combo items."
                ))
            if line.combo_item_id and line.combo_item_id.product_id != line.product_id:
                raise ValidationError(_(
                    "A sale order line's product must match its combo item's product."
                ))

    #=== ONCHANGE METHODS ===#

    @api.onchange('product_id')
    def _onchange_product_id_warning(self):
        if not self.product_id:
            return

        product = self.product_id
        if product.sale_line_warn != 'no-message':
            if product.sale_line_warn == 'block':
                self.product_id = False

            return {
                'warning': {
                    'title': _("Warning for %s", product.name),
                    'message': product.sale_line_warn_msg,
                }
            }

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        self._reset_price_unit()

    @api.onchange('product_packaging_id')
    def _onchange_product_packaging_id(self):
        if self.product_packaging_id and self.product_uom_qty:
            newqty = self.product_packaging_id._check_qty(self.product_uom_qty, self.product_uom, "UP")
            if float_compare(newqty, self.product_uom_qty, precision_rounding=self.product_uom.rounding) != 0:
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _(
                            "This product is packaged by %(pack_size).2f %(pack_name)s. You should sell %(quantity).2f %(unit)s.",
                            pack_size=self.product_packaging_id.qty,
                            pack_name=self.product_id.uom_id.name,
                            quantity=newqty,
                            unit=self.product_uom.name
                        ),
                    },
                }

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('display_type') or self.default_get(['display_type']).get('display_type'):
                vals['product_uom_qty'] = 0.0

            if 'technical_price_unit' in vals and 'price_unit' not in vals:
                # price_unit field was set as readonly in the view (but technical_price_unit not)
                # the field is not sent by the client and expected to be recomputed, but isn't
                # because technical_price_unit is set.
                vals.pop('technical_price_unit')

        lines = super().create(vals_list)
        for line in lines:
            linked_line = line._get_linked_line()
            if linked_line:
                line.linked_line_id = linked_line
        if self.env.context.get('sale_no_log_for_new_lines'):
            return lines

        for line in lines:
            if line.product_id and line.state == 'sale':
                msg = _("Extra line with %s", line.product_id.display_name)
                line.order_id.message_post(body=msg)

        return lines

    def _add_precomputed_values(self, vals_list):
        super()._add_precomputed_values(vals_list)
        for vals in vals_list:
            if 'price_unit' in vals and 'technical_price_unit' not in vals:
                vals['technical_price_unit'] = vals['price_unit']

    def write(self, values):
        if 'display_type' in values and self.filtered(lambda line: line.display_type != values.get('display_type')):
            raise UserError(_("You cannot change the type of a sale order line. Instead you should delete the current line and create a new line of the proper type."))

        if 'product_id' in values and any(
            sol.product_id.id != values['product_id']
            and not sol.product_updatable
            for sol in self
        ):
            raise UserError(_("You cannot modify the product of this order line."))

        if 'product_uom_qty' in values:
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            self.filtered(
                lambda r: r.state == 'sale' and float_compare(r.product_uom_qty, values['product_uom_qty'], precision_digits=precision) != 0)._update_line_quantity(values)

        if (
            'technical_price_unit' in values
            and 'price_unit' not in values
            and not self.env.context.get('sale_write_from_compute')
        ):
            # price_unit field was set as readonly in the view (but technical_price_unit not)
            # the field is not sent by the client and expected to be recomputed, but isn't
            # because technical_price_unit is set.
            values.pop('technical_price_unit')

        # Prevent writing on a locked SO.
        protected_fields = self._get_protected_fields()
        if any(self.order_id.mapped('locked')) and any(f in values.keys() for f in protected_fields):
            protected_fields_modified = list(set(protected_fields) & set(values.keys()))

            if 'name' in protected_fields_modified and all(self.mapped('is_downpayment')):
                protected_fields_modified.remove('name')

            fields = self.env['ir.model.fields'].sudo().search([
                ('name', 'in', protected_fields_modified), ('model', '=', self._name)
            ])
            if fields:
                raise UserError(
                    _('It is forbidden to modify the following fields in a locked order:\n%s',
                      '\n'.join(fields.mapped('field_description')))
                )

        result = super().write(values)

        # Don't recompute the package_id if we are setting the quantity of the items and the quantity of packages
        if 'product_uom_qty' in values and 'product_packaging_qty' in values and 'product_packaging_id' not in values:
            self.env.remove_to_compute(self._fields['product_packaging_id'], self)

        return result

    def _get_protected_fields(self):
        """ Give the fields that should not be modified on a locked SO.

        :returns: list of field names
        :rtype: list
        """
        return [
            'product_id', 'name', 'price_unit', 'product_uom', 'product_uom_qty',
            'tax_id', 'analytic_distribution'
        ]

    def _update_line_quantity(self, values):
        orders = self.mapped('order_id')
        for order in orders:
            order_lines = self.filtered(lambda x: x.order_id == order)
            msg = Markup("<b>%s</b><ul>") % _("The ordered quantity has been updated.")
            for line in order_lines:
                if 'product_id' in values and values['product_id'] != line.product_id.id:
                    # tracking is meaningless if the product is changed as well.
                    continue
                msg += Markup("<li> %s: <br/>") % line.product_id.display_name
                msg += _(
                    "Ordered Quantity: %(old_qty)s -> %(new_qty)s",
                    old_qty=line.product_uom_qty,
                    new_qty=values["product_uom_qty"]
                ) + Markup("<br/>")
                if line.product_id.type == 'consu':
                    msg += _("Delivered Quantity: %s", line.qty_delivered) + Markup("<br/>")
                msg += _("Invoiced Quantity: %s", line.qty_invoiced) + Markup("<br/>")
            msg += Markup("</ul>")
            order.message_post(body=msg)

    def _check_line_unlink(self):
        """ Check whether given lines can be deleted or not.

        * Lines cannot be deleted if the order is confirmed.
        * Down payment lines who have not yet been invoiced bypass that exception.
        * Sections and Notes can always be deleted.

        :returns: Sales Order Lines that cannot be deleted
        :rtype: `sale.order.line` recordset
        """
        return self.filtered(
            lambda line:
                line.state == 'sale'
                and (line.invoice_lines or not line.is_downpayment)
                and not line.display_type
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        if self._check_line_unlink():
            raise UserError(_("Once a sales order is confirmed, you can't remove one of its lines (we need to track if something gets invoiced or delivered).\n\
                Set the quantity to 0 instead."))

    #=== ACTION METHODS ===#

    def action_add_from_catalog(self):
        order = self.env['sale.order'].browse(self.env.context.get('order_id'))
        return order.with_context(child_field='order_line').action_add_from_catalog()

    #=== BUSINESS METHODS ===#

    def _expected_date(self):
        self.ensure_one()
        if self.state == 'sale' and self.order_id.date_order:
            order_date = self.order_id.date_order
        else:
            order_date = fields.Datetime.now()
        return order_date + timedelta(days=self.customer_lead or 0.0)

    def compute_uom_qty(self, new_qty, stock_move, rounding=True):
        return self.product_uom._compute_quantity(new_qty, stock_move.product_uom, rounding)

    def _get_invoice_line_sequence(self, new=0, old=0):
        """
        Method intended to be overridden in third-party module if we want to prevent the resequencing
        of invoice lines.

        :param int new:   the new line sequence
        :param int old:   the old line sequence

        :return:          the sequence of the SO line, by default the new one.
        """
        return new or old

    def _prepare_invoice_line(self, **optional_values):
        """Prepare the values to create the new invoice line for a sales order line.

        :param optional_values: any parameter that should be added to the returned invoice line
        :rtype: dict
        """
        self.ensure_one()

        if self.product_id.type == 'combo':
            # If the quantity to invoice is a whole number, format it as an integer (with no decimal point)
            qty_to_invoice = int(self.qty_to_invoice) if self.qty_to_invoice == int(self.qty_to_invoice) else self.qty_to_invoice
            return {
                'display_type': 'line_section',
                'sequence': self.sequence,
                'name': f'{self.product_id.name} x {qty_to_invoice}',
                'product_uom_id': self.product_uom.id,
                'quantity': self.qty_to_invoice,
                'sale_line_ids': [Command.link(self.id)],
                **optional_values,
            }
        res = {
            'display_type': self.display_type or 'product',
            'sequence': self.sequence,
            'name': self.env['account.move.line']._get_journal_items_full_name(self.name, self.product_id.display_name),
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'discount': self.discount,
            'price_unit': self.price_unit,
            'tax_ids': [Command.set(self.tax_id.ids)],
            'sale_line_ids': [Command.link(self.id)],
            'is_downpayment': self.is_downpayment,
        }
        downpayment_lines = self.invoice_lines.filtered('is_downpayment')
        if self.is_downpayment and downpayment_lines:
            res['account_id'] = downpayment_lines.account_id[:1].id
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res

    def _set_analytic_distribution(self, inv_line_vals, **optional_values):
        if self.analytic_distribution and not self.display_type:
            inv_line_vals['analytic_distribution'] = self.analytic_distribution

    def _prepare_procurement_values(self, group_id=False):
        """ Prepare specific key for moves or other components that will be created from a stock rule
        coming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        return {}

    def _validate_analytic_distribution(self):
        for line in self.filtered(lambda l: not l.display_type and l.state in ['draft', 'sent']):
            line._validate_distribution(**{
                'product': line.product_id.id,
                'business_domain': 'sale_order',
                'company_id': line.company_id.id,
            })

    def _get_downpayment_line_price_unit(self, invoices):
        return sum(
            l.price_unit if l.move_id.move_type == 'out_invoice' else -l.price_unit
            for l in self.invoice_lines
            if l.move_id.state == 'posted' and l.move_id not in invoices  # don't recompute with the final invoice
        )

    #=== CORE METHODS OVERRIDES ===#

    def _get_partner_display(self):
        self.ensure_one()
        commercial_partner = self.sudo().order_partner_id.commercial_partner_id
        return f'({commercial_partner.ref or commercial_partner.name})'

    def _additional_name_per_id(self):
        return {
            so_line.id: so_line._get_partner_display()
            for so_line in self
        }

    #=== HOOKS ===#

    def _is_delivery(self):
        self.ensure_one()
        return False

    def _is_not_sellable_line(self):
        # True if the line is a computed line (reward, delivery, ...) that user cannot add manually
        return False

    def _get_product_catalog_lines_data(self, **kwargs):
        """ Return information about sale order lines in `self`.

        If `self` is empty, this method returns only the default value(s) needed for the product
        catalog. In this case, the quantity that equals 0.

        Otherwise, it returns a quantity and a price based on the product of the SOL(s) and whether
        the product is read-only or not.

        A product is considered read-only if the order is considered read-only (see
        ``SaleOrder._is_readonly`` for more details) or if `self` contains multiple records
        or if it has sale_line_warn == "block".

        Note: This method cannot be called with multiple records that have different products linked.

        :raise odoo.exceptions.ValueError: ``len(self.product_id) != 1``
        :rtype: dict
        :return: A dict with the following structure:
            {
                'quantity': float,
                'price': float,
                'readOnly': bool,
                'warning': String
            }
        """
        if len(self) == 1:
            res = {
                'quantity': self.product_uom_qty,
                'price': self._get_discounted_price(),
                'readOnly': (
                    self.order_id._is_readonly()
                    or self.product_id.sale_line_warn == 'block'
                    or bool(self.combo_item_id)
                ),
            }
            if self.product_id.sale_line_warn != 'no-message' and self.product_id.sale_line_warn_msg:
                res['warning'] = self.product_id.sale_line_warn_msg
            return res
        elif self:
            self.product_id.ensure_one()
            order_line = self[0]
            order = order_line.order_id
            res = {
                'readOnly': True,
                'price': order.pricelist_id._get_product_price(
                    product=order_line.product_id,
                    quantity=1.0,
                    currency=order.currency_id,
                    date=order.date_order,
                    **kwargs,
                ),
                'quantity': sum(
                    self.mapped(
                        lambda line: line.product_uom._compute_quantity(
                            qty=line.product_uom_qty,
                            to_unit=line.product_id.uom_id,
                        )
                    )
                )
            }
            if self.product_id.sale_line_warn != 'no-message' and self.product_id.sale_line_warn_msg:
                res['warning'] = self.product_id.sale_line_warn_msg
            return res
        else:
            return {
                'quantity': 0,
                # price will be computed in batch with pricelist utils so not given here
            }

    #=== TOOLING ===#

    def _convert_to_sol_currency(self, amount, currency):
        """Convert the given amount from the given currency to the SO(L) currency.

        :param float amount: the amount to convert
        :param currency: currency in which the given amount is expressed
        :type currency: `res.currency` record
        :returns: converted amount
        :rtype: float
        """
        self.ensure_one()
        to_currency = self.currency_id or self.order_id.currency_id
        if currency and to_currency and currency != to_currency:
            conversion_date = self.order_id.date_order or fields.Date.context_today(self)
            company = self.company_id or self.order_id.company_id or self.env.company
            return currency._convert(
                from_amount=amount,
                to_currency=to_currency,
                company=company,
                date=conversion_date,
                round=False,
            )
        return amount

    def _get_discounted_price(self):
        self.ensure_one()
        return self.price_unit * (1 - (self.discount or 0.0) / 100.0)

    def has_valued_move_ids(self):
        return None  # TODO: remove in master

    def _get_linked_line(self):
        """ Return the linked line of this line, if any.

        This method relies on either `linked_line_id` or `linked_virtual_id` to retrieve the linked
        line, depending on whether the linked line is saved in the DB.
        """
        self.ensure_one()
        return self.linked_line_id or (
            self.linked_virtual_id and self.order_id.order_line.filtered(
                lambda line: line.virtual_id == self.linked_virtual_id
            ).ensure_one()
        ) or self.env['sale.order.line']

    def _get_linked_lines(self):
        """ Return the linked lines of this line, if any.

        This method relies on either `linked_line_id` or `linked_virtual_id` to retrieve the linked
        lines, depending on whether this line is saved in the DB.

        Note: we can't rely on `linked_line_ids` as it will only be populated when both this line
        and its linked lines are saved in the DB, which we can't ensure.
        """
        self.ensure_one()
        return (
            self._origin and self.order_id.order_line.filtered(
                lambda line: line.linked_line_id._origin == self._origin
            )
        ) or (
            self.virtual_id and self.order_id.order_line.filtered(
                lambda line: line.linked_virtual_id == self.virtual_id
            )
        ) or self.env['sale.order.line']

    def _sellable_lines_domain(self):
        discount_products_ids = self.env.companies.sale_discount_product_id.ids
        domain = [('is_downpayment', '=', False)]
        if discount_products_ids:
            domain = expression.AND([
                domain,
                [('product_id', 'not in', discount_products_ids)],
            ])
        return domain

    def _get_lines_with_price(self):
        """ A combo product line always has a zero price (by design). The actual price of the combo
        product can be computed by summing the prices of its combo items (i.e. its linked lines).
        """
        return self.linked_line_ids if self.product_type == 'combo' else self
