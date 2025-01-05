# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    sales_count = fields.Float(compute='_compute_sales_count', string='Sold', digits='Product Unit')

    # Catalog related fields
    product_catalog_product_is_in_sale_order = fields.Boolean(
        compute='_compute_product_is_in_sale_order',
        search='_search_product_is_in_sale_order',
    )

    def _compute_sales_count(self):
        r = {}
        self.sales_count = 0
        if not self.env.user.has_group('sales_team.group_sale_salesman'):
            return r
        date_from = fields.Date.today() - timedelta(days=365)

        done_states = self.env['sale.report']._get_done_states()

        domain = [
            ('state', 'in', done_states),
            ('product_id', 'in', self.ids),
            ('date', '>=', date_from),
        ]
        for product, product_uom_qty in self.env['sale.report']._read_group(domain, ['product_id'], ['product_uom_qty:sum']):
            r[product.id] = product_uom_qty
        for product in self:
            if not product.id:
                product.sales_count = 0.0
                continue
            product.sales_count = float_round(r.get(product.id, 0), precision_rounding=product.uom_id.rounding)
        return r

    @api.onchange('type')
    def _onchange_type(self):
        if self._origin and self.sales_count > 0:
            return {'warning': {
                'title': _("Warning"),
                'message': _("You cannot change the product's type because it is already used in sales orders.")
            }}

    @api.depends_context('order_id')
    def _compute_product_is_in_sale_order(self):
        order_id = self.env.context.get('order_id')
        if not order_id:
            self.product_catalog_product_is_in_sale_order = False
            return

        read_group_data = self.env['sale.order.line']._read_group(
            domain=[('order_id', '=', order_id)],
            groupby=['product_id'],
            aggregates=['__count'],
        )
        data = {product.id: count for product, count in read_group_data}
        for product in self:
            product.product_catalog_product_is_in_sale_order = bool(data.get(product.id, 0))

    def _search_product_is_in_sale_order(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_("Operation not supported"))
        product_ids = self.env['sale.order.line'].search([
            ('order_id', 'in', [self.env.context.get('order_id', '')]),
        ]).product_id.ids
        return [('id', 'in', product_ids)]

    @api.readonly
    def action_view_sales(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.report_all_channels_sales_action")
        action['domain'] = [('product_id', 'in', self.ids)]
        action['context'] = {
            'pivot_measures': ['product_uom_qty'],
            'active_id': self._context.get('active_id'),
            'search_default_Sales': 1,
            'active_model': 'sale.report',
            'search_default_filter_order_date': 1,
        }
        return action

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [self.env.ref('sale.sale_menu_root').id]

    def _get_invoice_policy(self):
        return self.invoice_policy

    def _filter_to_unlink(self):
        domain = [('product_id', 'in', self.ids)]
        lines = self.env['sale.order.line']._read_group(domain, ['product_id'])
        linked_product_ids = [product.id for [product] in lines]
        return super(ProductProduct, self - self.browse(linked_product_ids))._filter_to_unlink()


class ProductAttributeCustomValue(models.Model):
    _inherit = "product.attribute.custom.value"

    sale_order_line_id = fields.Many2one('sale.order.line', string="Sales Order Line", ondelete='cascade')

    _sol_custom_value_unique = models.Constraint(
        'unique(custom_product_template_attribute_value_id, sale_order_line_id)',
        'Only one Custom Value is allowed per Attribute Value per Sales Order Line.',
    )
