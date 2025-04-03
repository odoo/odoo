# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _check_company_auto = True

    service_type = fields.Selection(
        selection=[('manual', "Manually set quantities on order")],
        string="Track Service",
        compute='_compute_service_type', store=True, readonly=False, precompute=True,
        help="Manually set quantities on order: Invoice based on the manually entered quantity, without creating an analytic account.\n"
             "Timesheets on contract: Invoice based on the tracked hours on the related timesheet.\n"
             "Create a task and track hours: Create a task on the sales order validation and track the work hours.")
    sale_line_warn_msg = fields.Text(string="Sales Order Line Warning")
    expense_policy = fields.Selection(
        selection=[
            ('no', "No"),
            ('cost', "At cost"),
            ('sales_price', "Sales price"),
        ],
        string="Re-Invoice Costs", default='no',
        compute='_compute_expense_policy', store=True, readonly=False,
        help="Validated expenses, vendor bills, or stock pickings (set up to track costs) can be invoiced to the customer at either cost or sales price.")
    visible_expense_policy = fields.Boolean(
        string="Re-Invoice Policy visible", compute='_compute_visible_expense_policy')
    sales_count = fields.Float(
        string="Sold", compute='_compute_sales_count', digits='Product Unit')
    invoice_policy = fields.Selection(
        selection=[
            ('order', "Ordered quantities"),
            ('delivery', "Delivered quantities"),
        ],
        string="Invoicing Policy",
        compute='_compute_invoice_policy',
        precompute=True,
        store=True,
        readonly=False,
        tracking=True,
        help="Ordered Quantity: Invoice quantities ordered by the customer.\n"
             "Delivered Quantity: Invoice quantities delivered to the customer.")
    optional_product_ids = fields.Many2many(
        comodel_name='product.template',
        relation='product_optional_rel',
        column1='src_id',
        column2='dest_id',
        string="Optional Products",
        help="Optional Products are suggested "
             "whenever the customer hits *Add to Cart* (cross-sell strategy, "
             "e.g. for computers: warranty, software, etc.).",
        check_company=True)

    @api.depends('invoice_policy', 'sale_ok', 'service_tracking')
    def _compute_product_tooltip(self):
        super()._compute_product_tooltip()

    def _prepare_tooltip(self):
        tooltip = super()._prepare_tooltip()
        if not self.sale_ok:
            return tooltip

        invoicing_tooltip = self._prepare_invoicing_tooltip()

        tooltip = f'{tooltip} {invoicing_tooltip}' if tooltip else invoicing_tooltip

        if self.type == 'service':
            additional_tooltip = self._prepare_service_tracking_tooltip()
            tooltip = f'{tooltip} {additional_tooltip}' if additional_tooltip else tooltip

        return tooltip

    def _prepare_invoicing_tooltip(self):
        if self.invoice_policy == 'delivery' and self.type != 'consu':
            return _("Invoice after delivery, based on quantities delivered, not ordered.")
        elif self.invoice_policy == 'order' and self.type == 'service':
            return _("Invoice ordered quantities as soon as this service is sold.")
        return ""

    def _prepare_service_tracking_tooltip(self):
        return ""

    @api.depends('sale_ok')
    def _compute_service_tracking(self):
        super()._compute_service_tracking()
        self.filtered(lambda pt: not pt.sale_ok).service_tracking = 'no'

    @api.depends('purchase_ok')
    def _compute_visible_expense_policy(self):
        visibility = self.env.user.has_group('analytic.group_analytic_accounting')
        for product_template in self:
            product_template.visible_expense_policy = visibility and product_template.purchase_ok

    @api.depends('sale_ok')
    def _compute_expense_policy(self):
        self.filtered(lambda t: not t.sale_ok).expense_policy = 'no'

    @api.depends('product_variant_ids.sales_count')
    def _compute_sales_count(self):
        for product in self:
            product.sales_count = product.uom_id.round(sum(p.sales_count for p in product.with_context(active_test=False).product_variant_ids))

    @api.constrains('company_id')
    def _check_sale_product_company(self):
        """Ensure the product is not being restricted to a single company while
        having been sold in another one in the past, as this could cause issues."""
        products_by_compagny = defaultdict(lambda: self.env['product.template'])
        for product in self:
            if not product.product_variant_ids or not product.company_id:
                # No need to check if the product has just being created (`product_variant_ids` is
                # still empty) or if we're writing `False` on its company (should always work.)
                continue
            products_by_compagny[product.company_id] |= product

        for target_company, products in products_by_compagny.items():
            subquery_products = self.env['product.product'].sudo().with_context(active_test=False)._search([('product_tmpl_id', 'in', products.ids)])
            so_lines = self.env['sale.order.line'].sudo().search_read(
                [('product_id', 'in', subquery_products), '!', ('company_id', 'child_of', target_company.id)],
                fields=['id', 'product_id'])
            if so_lines:
                used_products = [sol['product_id'][1] for sol in so_lines]
                raise ValidationError(_('The following products cannot be restricted to the company'
                                        ' %(company)s because they have already been used in quotations or '
                                        'sales orders in another company:\n%(used_products)s\n'
                                        'You can archive these products and recreate them '
                                        'with your company restriction instead, or leave them as '
                                        'shared product.', company=target_company.name, used_products=', '.join(used_products)))

    @api.readonly
    def action_view_sales(self):
        action = self.env['ir.actions.actions']._for_xml_id('sale.report_all_channels_sales_action')
        action['domain'] = [('product_tmpl_id', 'in', self.ids)]
        action['context'] = {
            'pivot_measures': ['product_uom_qty'],
            'active_id': self.env.context.get('active_id'),
            'active_model': 'sale.report',
            'search_default_Sales': 1,
            'search_default_filter_order_date': 1,
            'search_default_group_by_date': 1,
        }
        return action

    @api.onchange('type')
    def _onchange_type(self):
        res = super()._onchange_type()
        if self._origin and self.sales_count > 0:
            res['warning'] = {
                'title': _("Warning"),
                'message': _("You cannot change the product's type because it is already used in sales orders.")
            }
        return res

    @api.depends('type')
    def _compute_service_type(self):
        self.filtered(lambda t: t.type == 'consu' or not t.service_type).service_type = 'manual'

    @api.depends('type')
    def _compute_invoice_policy(self):
        self.filtered(lambda t: t.type == 'consu' or not t.invoice_policy).invoice_policy = 'order'

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [self.env.ref('sale.sale_menu_root').id]

    @api.model
    def get_import_templates(self):
        res = super(ProductTemplate, self).get_import_templates()
        if self.env.context.get('sale_multi_pricelist_product_template'):
            if self.env.user.has_group('product.group_product_pricelist'):
                return [{
                    'label': _("Import Template for Products"),
                    'template': '/product/static/xls/product_template.xls'
                }]
        return res

    @api.model
    def _get_incompatible_types(self):
        return []

    @api.constrains(lambda self: self._get_incompatible_types())
    def _check_incompatible_types(self):
        incompatible_types = self._get_incompatible_types()
        if len(incompatible_types) < 2:
            return
        fields = self.env['ir.model.fields'].sudo().search_read(
            [('model', '=', 'product.template'), ('name', 'in', incompatible_types)],
            ['name', 'field_description'])
        field_descriptions = {v['name']: v['field_description'] for v in fields}
        field_list = incompatible_types + ['name']
        values = self.read(field_list)
        for val in values:
            incompatible_fields = [f for f in incompatible_types if val[f]]
            if len(incompatible_fields) > 1:
                raise ValidationError(_(
                    "The product (%(product)s) has incompatible values: %(value_list)s",
                    product=val['name'],
                    value_list=[field_descriptions[v] for v in incompatible_fields],
                ))

    def get_single_product_variant(self):
        """ Method used by the product configurator to check if the product is configurable or not.

        We need to open the product configurator if the product:
        - is configurable (see has_configurable_attributes)
        - has optional products """
        res = super().get_single_product_variant()
        if res.get('product_id', False):
            has_optional_products = False
            for optional_product in self.product_variant_id.optional_product_ids:
                if optional_product.has_dynamic_attributes() or optional_product._get_possible_variants(
                    self.product_variant_id.product_template_attribute_value_ids
                ):
                    has_optional_products = True
                    break
            res.update({
                'has_optional_products': has_optional_products,
                'is_combo': self.type == 'combo',
            })
        return res

    @api.model
    def _get_saleable_tracking_types(self):
        """Return list of salealbe service_tracking types.

        :rtype: list
        """
        return ['no']

    ####################################
    # Product/combo configurator hooks #
    ####################################

    @api.model
    def _get_configurator_display_price(
        self, product_or_template, quantity, date, currency, pricelist, **kwargs
    ):
        """ Return the specified product's display price, to be used by the product and combo
        configurators.

        This is a hook meant to customize the display price computation in overriding modules.

        :param product.product|product.template product_or_template: The product for which to get
            the price.
        :param int quantity: The quantity of the product.
        :param datetime date: The date to use to compute the price.
        :param res.currency currency: The currency to use to compute the price.
        :param product.pricelist pricelist: The pricelist to use to compute the price.
        :param dict kwargs: Locally unused data passed to `_get_configurator_price`.
        :rtype: tuple(float, int or False)
        :return: The specified product's display price (and the applied pricelist rule)
        """
        return self._get_configurator_price(
            product_or_template, quantity, date, currency, pricelist, **kwargs
        )

    @api.model
    def _get_configurator_price(
        self, product_or_template, quantity, date, currency, pricelist, **kwargs
    ):
        """ Return the specified product's price, to be used by the product and combo configurators.

        This is a hook meant to customize the price computation in overriding modules.

        This hook has been extracted from `_get_configurator_display_price` because the price
        computation can be overridden in 2 ways:

        - Either by transforming super's price (e.g. in `website_sale`, we apply taxes to the
          price),
        - Or by computing a different price (e.g. in `sale_subscription`, we ignore super when
          computing subscription prices).
        In some cases, the order of the overrides matters, which is why we need 2 separate methods
        (e.g. in `website_sale_subscription`, we must compute the subscription price before applying
        taxes).

        :param product.product|product.template product_or_template: The product for which to get
            the price.
        :param int quantity: The quantity of the product.
        :param datetime date: The date to use to compute the price.
        :param res.currency currency: The currency to use to compute the price.
        :param product.pricelist pricelist: The pricelist to use to compute the price.
        :param dict kwargs: Locally unused data passed to `_get_product_price`.
        :rtype: tuple(float, int or False)
        :return: The specified product's price (and the applied pricelist rule)
        """
        return pricelist._get_product_price_rule(
            product_or_template, quantity=quantity, currency=currency, date=date, **kwargs
        )

    @api.model
    def _get_additional_configurator_data(
        self, product_or_template, date, currency, pricelist, *, uom=None, **kwargs
    ):
        """Return additional data about the specified product.

        This is a hook meant to append module-specific data in overriding modules.

        :param product.product|product.template product_or_template: The product for which to get
            additional data.
        :param datetime date: The date to use to compute prices.
        :param res.currency currency: The currency to use to compute prices.
        :param product.pricelist pricelist: The pricelist to use to compute prices.
        :param uom.uom uom: The uom to use to compute prices.
        :param dict kwargs: Locally unused data passed to overrides.
        :rtype: dict
        :return: A dict containing additional data about the specified product.
        """
        return {}
