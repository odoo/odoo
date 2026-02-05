# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime

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
                    'template': '/product/static/xls/products_import_template.xlsx'
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

    def get_single_product_variant(self, quantity=1):
        """ Method used by the product configurator to check if the product is configurable or not.

        We need to open the product configurator if the product:
        - is configurable (see has_configurable_attributes)
        - has optional products """
        res = super().get_single_product_variant(quantity)
        if res.get('product_id', False):
            has_optional_products = False
            for optional_product in self.product_variant_id.optional_product_ids:
                if optional_product.has_dynamic_attributes() or optional_product._get_possible_variants():
                    has_optional_products = True
                    break
            res.update({
                'has_optional_products': has_optional_products,
                'is_combo': self.type == 'combo',
            })

        if not res.get('product_id') or res.get('has_optional_products'):

            preloaded_data = self.sale_product_configurator_get_values(
                product_template_id=self.id,
                quantity=quantity,
                currency_id=self.env.company.currency_id.id,
                so_date=fields.Datetime.now().isoformat(),
                only_main_product=False
            )
            res['preloaded_config_data'] = preloaded_data

        return res

    def sale_product_configurator_get_values(
        self,
        product_template_id,
        quantity,
        currency_id,
        so_date,
        product_uom_id=None,
        company_id=None,
        pricelist_id=None,
        ptav_ids=None,
        only_main_product=False,
        **kwargs,
    ):
        """Return all product information needed for the product configurator.

        :param int product_template_id: The product for which to seek information, as a
            `product.template` id.
        :param int quantity: The quantity of the product.
        :param int currency_id: The currency of the transaction, as a `res.currency` id.
        :param str so_date: The date of the `sale.order`, to compute the price at the right rate.
        :param int|None product_uom_id: The unit of measure of the product, as a `uom.uom` id.
        :param int|None company_id: The company to use, as a `res.company` id.
        :param int|None pricelist_id: The pricelist to use, as a `product.pricelist` id.
        :param list(int)|None ptav_ids: The combination of the product, as a list of
            `product.template.attribute.value` ids.
        :param bool only_main_product: Whether the optional products should be included or not.
        :param dict kwargs: Locally unused data passed to `_get_product_information`.
        :rtype: dict
        :return: A dict containing a list of products and a list of optional products information,
            generated by :meth:`_get_product_information`.
        """
        if company_id:
            self.update_context(allowed_company_ids=[company_id])
        product_template = self._get_product_template(product_template_id)

        combination = self.env['product.template.attribute.value']
        if ptav_ids:
            combination = self.env['product.template.attribute.value'].browse(ptav_ids).filtered(
                lambda ptav: ptav.product_tmpl_id.id == product_template_id
            )
            # Set missing attributes (unsaved no_variant attributes, or new attribute on existing product)
            unconfigured_ptals = (
                product_template.attribute_line_ids - combination.attribute_line_id).filtered(
                lambda ptal: ptal.attribute_id.display_type != 'multi')
            combination += unconfigured_ptals.mapped(
                lambda ptal: ptal.product_template_value_ids._only_active()[:1]
            )
        if not combination:
            combination = product_template._get_first_possible_combination()
        currency = self.env['res.currency'].browse(currency_id)
        pricelist = self.env['product.pricelist'].browse(pricelist_id)
        so_date = datetime.fromisoformat(so_date).date()

        return {
            'products': [
                dict(
                    **self._get_product_information(
                        product_template,
                        combination,
                        currency,
                        pricelist,
                        so_date,
                        quantity=quantity,
                        product_uom_id=product_uom_id,
                        **kwargs,
                    ),
                )
            ],
            'optional_products': [
                dict(
                    **self._get_product_information(
                        optional_product_template,
                        optional_product_template._get_first_possible_combination(),
                        currency,
                        pricelist,
                        so_date,
                        **kwargs,
                    ),
                    parent_product_tmpl_id=product_template.id,
                ) for optional_product_template in product_template.optional_product_ids if
                self._should_show_product(optional_product_template)
            ] if not only_main_product else [],
            'currency_id': currency_id,
        }

    def _get_product_information(
        self,
        product_template,
        combination,
        currency,
        pricelist,
        so_date,
        quantity=1,
        product_uom_id=None,
        show_packaging=True,
        **kwargs,
    ):
        """Return complete information about a product.

        :param product.template product_template: The product for which to seek information.
        :param product.template.attribute.value combination: The combination of the product.
        :param res.currency currency: The currency of the transaction.
        :param product.pricelist pricelist: The pricelist to use.
        :param datetime so_date: The date of the `sale.order`, to compute the price at the right
            rate.
        :param int quantity: The quantity of the product.
        :param int|None product_uom_id: The unit of measure of the product, as a `uom.uom` id.
        :param dict kwargs: Locally unused data passed to `_get_basic_product_information`.
        :rtype: dict
        :return: A dict with the following structure:
            {
                'product_tmpl_id': int,
                'id': int,
                'description_sale': str|False,
                'display_name': str,
                'price': float,
                'quantity': int
                'attribute_line': [{
                    'id': int
                    'attribute': {
                        'id': int
                        'name': str
                        'display_type': str
                    },
                    'attribute_value': [{
                        'id': int,
                        'name': str,
                        'price_extra': float,
                        'html_color': str|False,
                        'image': str|False,
                        'is_custom': bool
                    }],
                    'selected_attribute_id': int,
                }],
                'exclusions': dict,
                'archived_combination': dict,
                'available_uoms': dict (optional),
            }
        """
        uom = (
            (product_uom_id and self.env['uom.uom'].browse(product_uom_id))
            or product_template.uom_id
        )
        product = product_template._get_variant_for_combination(combination)
        attribute_exclusions = product_template._get_attribute_exclusions(
            combination_ids=combination.ids,
        )
        product_or_template = product or product_template
        ptals = product_template.attribute_line_ids
        attrs_map = {
            attr_data['id']: attr_data
            for attr_data in ptals.attribute_id.read(['id', 'name', 'display_type'])
        }
        ptavs = ptals.product_template_value_ids.filtered(lambda p: p.ptav_active or combination and p.id in combination.ids)
        ptavs_map = dict(zip(ptavs.ids, ptavs.read(['name', 'html_color', 'image', 'is_custom'])))

        values = dict(
            product_tmpl_id=product_template.id,
            **self._get_basic_product_information(
                product_or_template,
                pricelist,
                combination,
                quantity=quantity,
                uom=uom,
                currency=currency,
                date=so_date,
                **kwargs,
            ),
            quantity=quantity,
            uom=uom.read(['id', 'display_name'])[0],
            attribute_lines=[{
                'id': ptal.id,
                'attribute': dict(**attrs_map[ptal.attribute_id.id]),
                'attribute_values': [
                    dict(
                        **ptavs_map[ptav.id],
                        price_extra=self._get_ptav_price_extra(
                            ptav, currency, so_date, product_or_template
                        ),
                    ) for ptav in ptal.product_template_value_ids
                    if ptav.ptav_active or (combination and ptav.id in combination.ids)
                ],
                'selected_attribute_value_ids': combination.filtered(
                    lambda c: ptal in c.attribute_line_id
                ).ids,
                'create_variant': ptal.attribute_id.create_variant,
            } for ptal in product_template.attribute_line_ids],
            exclusions=attribute_exclusions['exclusions'],
            archived_combinations=attribute_exclusions['archived_combinations'],
        )
        if show_packaging and product_template._has_multiple_uoms():
            values['available_uoms'] = product_template._get_available_uoms().read(
                ['id', 'display_name']
            )
        # Shouldn't be sent client-side
        values.pop('pricelist_rule_id', None)
        return values

    def _get_basic_product_information(self, product_or_template, pricelist, combination, **kwargs):
        """Return basic information about a product.

        :param product.product|product.template product_or_template: The product for which to seek
            information.
        :param product.pricelist pricelist: The pricelist to use.
        :param product.template.attribute.value combination: The combination of the product.
        :param dict kwargs: Locally unused data passed to `_get_product_price`.
        :rtype: dict
        :return: A dict with the following structure:
            {
                'id': int,  # if product_or_template is a record of `product.product`.
                'description_sale': str|False,
                'display_name': str,
                'price': float,
            }
        """
        basic_information = dict(
            **product_or_template.read(['description_sale', 'display_name'])[0]
        )
        # If the product is a template, check the combination to compute the name to take dynamic
        # and no_variant attributes into account. Also, drop the id which was auto-included by the
        # search but isn't relevant since it is supposed to be the id of a `product.product` record.
        if not product_or_template.is_product_variant:
            basic_information['id'] = False
            combination_name = combination._get_combination_name()
            if combination_name:
                basic_information.update(
                    display_name=f"{basic_information['display_name']} ({combination_name})"
                )
        price, pricelist_rule_id = self.env['product.template']._get_configurator_display_price(
            product_or_template.with_context(
                **product_or_template._get_product_price_context(combination)
            ),
            pricelist=pricelist,
            **kwargs,
        )
        return dict(
            **basic_information,
            price=price,
            pricelist_rule_id=pricelist_rule_id,
            **self.env['product.template']._get_additional_configurator_data(
                product_or_template, pricelist=pricelist, **kwargs
            ),
        )

    def _get_ptav_price_extra(self, ptav, currency, date, product_or_template):
        """Return the extra price for a product template attribute value.

        :param product.template.attribute.value ptav: The product template attribute value for which
            to compute the extra price.
        :param res.currency currency: The currency to compute the extra price in.
        :param datetime date: The date to compute the extra price at.
        :param product.product|product.template product_or_template: The product on which the
            product template attribute value applies.
        :rtype: float
        :return: The extra price for the product template attribute value.
        """
        return ptav.currency_id._convert(
            ptav.price_extra,
            currency,
            self.env.company,
            date,
        )

    def _should_show_product(self, product_template):
        """Decide whether a product should be shown in the configurator.

        :param product.template product_template: The product being checked.
        :rtype: bool
        :return: Whether the product should be shown in the configurator.
        """
        return True

    def _get_product_template(self, product_template_id):
        return self.env['product.template'].browse(product_template_id)

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
