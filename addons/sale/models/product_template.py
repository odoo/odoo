# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _default_visible_expense_policy(self):
        return self.user_has_groups('analytic.group_analytic_accounting')

    service_type = fields.Selection([('manual', 'Manually set quantities on order')], string='Track Service',
        help="Manually set quantities on order: Invoice based on the manually entered quantity, without creating an analytic account.\n"
             "Timesheets on contract: Invoice based on the tracked hours on the related timesheet.\n"
             "Create a task and track hours: Create a task on the sales order validation and track the work hours.",
        default='manual')
    sale_line_warn = fields.Selection(WARNING_MESSAGE, 'Sales Order Line', help=WARNING_HELP, required=True, default="no-message")
    sale_line_warn_msg = fields.Text('Message for Sales Order Line')
    expense_policy = fields.Selection(
        [('no', 'No'), ('cost', 'At cost'), ('sales_price', 'Sales price')],
        string='Re-Invoice Expenses',
        default='no',
        help="Expenses and vendor bills can be re-invoiced to a customer."
             "With this option, a validated expense can be re-invoice to a customer at its cost or sales price.")
    visible_expense_policy = fields.Boolean("Re-Invoice Policy visible", compute='_compute_visible_expense_policy', default=lambda self: self._default_visible_expense_policy())
    sales_count = fields.Float(compute='_compute_sales_count', string='Sold')
    invoice_policy = fields.Selection([
        ('order', 'Ordered quantities'),
        ('delivery', 'Delivered quantities')], string='Invoicing Policy',
        help='Ordered Quantity: Invoice quantities ordered by the customer.\n'
             'Delivered Quantity: Invoice quantities delivered to the customer.',
        default='order')

    @api.depends('name')
    def _compute_visible_expense_policy(self):
        visibility = self.user_has_groups('analytic.group_analytic_accounting')
        for product_template in self:
            product_template.visible_expense_policy = visibility


    @api.onchange('sale_ok')
    def _change_sale_ok(self):
        if not self.sale_ok:
            self.expense_policy = 'no'

    @api.depends('product_variant_ids.sales_count')
    def _compute_sales_count(self):
        for product in self:
            product.sales_count = float_round(sum([p.sales_count for p in product.with_context(active_test=False).product_variant_ids]), precision_rounding=product.uom_id.rounding)


    @api.constrains('company_id')
    def _check_sale_product_company(self):
        """Ensure the product is not being restricted to a single company while
        having been sold in another one in the past, as this could cause issues."""
        target_company = self.company_id
        if target_company:  # don't prevent writing `False`, should always work
            product_data = self.env['product.product'].sudo().with_context(active_test=False).search_read([('product_tmpl_id', 'in', self.ids)], fields=['id'])
            product_ids = list(map(lambda p: p['id'], product_data))
            so_lines = self.env['sale.order.line'].sudo().search_read([('product_id', 'in', product_ids), ('company_id', '!=', target_company.id)], fields=['id', 'product_id'])
            used_products = list(map(lambda sol: sol['product_id'][1], so_lines))
            if so_lines:
                raise ValidationError(_('The following products cannot be restricted to the company'
                                        ' %s because they have already been used in quotations or '
                                        'sales orders in another company:\n%s\n'
                                        'You can archive these products and recreate them '
                                        'with your company restriction instead, or leave them as '
                                        'shared product.') % (target_company.name, ', '.join(used_products)))

    def action_view_sales(self):
        action = self.env.ref('sale.report_all_channels_sales_action').read()[0]
        action['domain'] = [('product_tmpl_id', 'in', self.ids)]
        action['context'] = {
            'pivot_measures': ['product_uom_qty'],
            'active_id': self._context.get('active_id'),
            'active_model': 'sale.report',
            'search_default_Sales': 1,
            'time_ranges': {'field': 'date', 'range': 'last_365_days'}
        }
        return action

    def create_product_variant(self, product_template_attribute_value_ids):
        """ Create if necessary and possible and return the id of the product
        variant matching the given combination for this template.

        Note AWA: Known "exploit" issues with this method:

        - This method could be used by an unauthenticated user to generate a
            lot of useless variants. Unfortunately, after discussing the
            matter with ODO, there's no easy and user-friendly way to block
            that behavior.

            We would have to use captcha/server actions to clean/... that
            are all not user-friendly/overkill mechanisms.

        - This method could be used to try to guess what product variant ids
            are created in the system and what product template ids are
            configured as "dynamic", but that does not seem like a big deal.

        The error messages are identical on purpose to avoid giving too much
        information to a potential attacker:
            - returning 0 when failing
            - returning the variant id whether it already existed or not

        :param product_template_attribute_value_ids: the combination for which
            to get or create variant
        :type product_template_attribute_value_ids: json encoded list of id
            of `product.template.attribute.value`

        :return: id of the product variant matching the combination or 0
        :rtype: int
        """
        combination = self.env['product.template.attribute.value'] \
            .browse(json.loads(product_template_attribute_value_ids))

        return self._create_product_variant(combination, log_warning=True).id or 0

    @api.onchange('type')
    def _onchange_type(self):
        """ Force values to stay consistent with integrity constraints """
        res = super(ProductTemplate, self)._onchange_type()
        if self.type == 'consu':
            if not self.invoice_policy:
                self.invoice_policy = 'order'
            self.service_type = 'manual'
        return res

    @api.model
    def get_import_templates(self):
        res = super(ProductTemplate, self).get_import_templates()
        if self.env.context.get('sale_multi_pricelist_product_template'):
            if self.user_has_groups('product.group_sale_pricelist'):
                return [{
                    'label': _('Import Template for Products'),
                    'template': '/product/static/xls/product_template.xls'
                }]
        return res

    def _get_combination_info(self, combination=False, product_id=False, add_qty=1, pricelist=None, parent_combination=False, only_template=False, currency=None):
        """ Return info about a given combination.

        Note: this method does not take into account whether the combination is
        actually possible.

        :param combination: recordset of `product.template.attribute.value`

        :param product_id: id of a `product.product`. If no `combination`
            is set, the method will try to load the variant `product_id` if
            it exists instead of finding a variant based on the combination.

            If there is no combination, that means we definitely want a
            variant and not something that will have no_variant set.

        :param add_qty: float with the quantity for which to get the info,
            indeed some pricelist rules might depend on it.

        :param pricelist: `product.pricelist` the pricelist to use
            (can be none, eg. from SO if no partner and no pricelist selected)

        :param parent_combination: if no combination and no product_id are
            given, it will try to find the first possible combination, taking
            into account parent_combination (if set) for the exclusion rules.

        :param only_template: boolean, if set to True, get the info for the
            template only: ignore combination and don't try to find variant

        :return: dict with product/combination info:

            - product_id: the variant id matching the combination (if it exists)

            - product_template_id: the current template id

            - display_name: the name of the combination

            - price: the computed price of the combination, take the catalog
                price if no pricelist is given

            - list_price: the catalog price of the combination, but this is
                not the "real" list_price, it has price_extra included (so
                it's actually more closely related to `lst_price`), and it
                is converted to the pricelist currency (if given)

            - has_discounted_price: True if the pricelist discount policy says
                the price does not include the discount and there is actually a
                discount applied (price < list_price), else False
        """
        self.ensure_one()
        # get the name before the change of context to benefit from prefetch
        display_name = self.display_name
        combination = combination or self.env['product.template.attribute.value']
        pricelist = pricelist or self.env['product.pricelist']
        currency = currency or pricelist.currency_id or self.currency_id
        # company = self.company_id or pricelist.company_id or self.env.company
        # VFE FIXME multi company checks

        # VFE TODO remove this context bullshit at this step ?
        quantity = self.env.context.get('quantity', add_qty)

        if not product_id and not combination and not only_template:
            combination = self._get_first_possible_combination(parent_combination)

        if only_template:
            product = self.env['product.product']
        elif product_id and not combination:
            product = self.env['product.product'].browse(product_id)
        else:
            product = self._get_variant_for_combination(combination)

        # We need to add the price_extra for the attributes that are not
        # in the variant, typically those of type no_variant, but it is
        # possible that a no_variant attribute is still in a variant if
        # the type of the attribute has been changed after creation.
        # depends on context ptav_ids, pricelist_id, uom_id, quantity
        if product:
            product = product.with_context(ptav_ids=tuple(combination.ids))
        else:
            self = self.with_context(ptav_ids=tuple(combination.ids))
        price = price_without_discount = 0.0
        pricelist_kwargs = dict(
            product=product or self,
            quantity=quantity,
            uom=self.uom_id,
            date=fields.Date.today(),
            currency=currency,
        )
        price, price_without_discount = pricelist._get_detailed_prices(**pricelist_kwargs)

        if product:
            display_image = bool(product.image_1920)
            display_name = product.display_name
        else:
            display_image = bool(self.image_1920)

            combination_name = combination._get_combination_name()
            if combination_name:
                display_name = "%s (%s)" % (display_name, combination_name)

        return {
            'product_id': product.id,
            'product_template_id': self.id,
            'display_name': display_name,
            'display_image': display_image,
            'price': price,
            'list_price': price_without_discount,
            'has_discounted_price': price_without_discount != price,
        }

    def _is_add_to_cart_possible(self, parent_combination=None):
        """
        It's possible to add to cart (potentially after configuration) if
        there is at least one possible combination.

        :param parent_combination: the combination from which `self` is an
            optional or accessory product.
        :type parent_combination: recordset `product.template.attribute.value`

        :return: True if it's possible to add to cart, else False
        :rtype: bool
        """
        self.ensure_one()
        if not self.active:
            # for performance: avoid calling `_get_possible_combinations`
            return False
        return next(self._get_possible_combinations(parent_combination), False) is not False
