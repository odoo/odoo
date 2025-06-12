# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    sales_count = fields.Float(compute='_compute_sales_count', string='Sold', digits='Product Unit')
    last_invoice_date = fields.Date(compute='_compute_last_invoice_date')

    # Catalog related fields
    product_catalog_product_is_in_sale_order = fields.Boolean(
        compute='_compute_product_is_in_sale_order',
        search='_search_product_is_in_sale_order',
    )

    @api.depends_context('partner_id')
    def _compute_last_invoice_date(self):
        self.last_invoice_date = False
        partner_id = self.env.context.get('partner_id')
        if not partner_id:
            return

        today = fields.Date.today()
        prioritized_product_and_time = self.env['product.template']._get_products_and_most_recent_invoice_date(partner_id, 'sale', self.ids)
        dates_by_product = defaultdict(lambda: False)
        for data in prioritized_product_and_time:
            date = data['invoice_date']
            product = self.browse(data['product_id'])
            if not dates_by_product[product] or date > dates_by_product[product]:
                dates_by_product[product] = date if date <= today else today
        for (product, date) in dates_by_product.items():
            product.last_invoice_date = date

    @api.depends_context('formatted_display_name', 'partner_id', 'prioritize_for')
    def _compute_display_name(self):
        super()._compute_display_name()

        # Add last invoiced date beside the product's name.
        if self.env.context.get('formatted_display_name') and\
            self.env['product.template']._must_prioritize_invoiced_product():
            today = fields.Date.today()
            for product in self:
                if product.last_invoice_date:
                    days_count = (today - product.last_invoice_date).days
                    if days_count > 365:
                        day_value_str = self.env._('%(years_count)sy', years_count=(days_count // 365))
                    elif days_count > 30:
                        day_value_str = self.env._('%(months_count)smo', months_count=(days_count // 30))
                    else:
                        day_value_str = self.env._('%(days_count)sd', days_count=days_count)
                    product.display_name += f'\t`{day_value_str}`'

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
            product.sales_count = product.uom_id.round(r.get(product.id, 0))
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
        if operator != 'in':
            return NotImplemented
        product_ids = self.env['sale.order.line'].search_fetch([
            ('order_id', 'in', [self.env.context.get('order_id', '')]),
        ], ['product_id']).product_id.ids
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

    def _update_uom(self, to_uom_id):
        for uom, product, so_lines in self.env['sale.order.line']._read_group(
            [('product_id', 'in', self.ids)],
            ['product_uom_id', 'product_id'],
            ['id:recordset'],
        ):
            if so_lines.product_uom_id != product.product_tmpl_id.uom_id:
                raise UserError(_(
                    'As other units of measure (ex : %(problem_uom)s) '
                    'than %(uom)s have already been used for this product, the change of unit of measure can not be done.'
                    'If you want to change it, please archive the product and create a new one.',
                    problem_uom=uom.display_name, uom=product.product_tmpl_id.uom_id.display_name))
            so_lines.product_uom_id = to_uom_id
        return super()._update_uom(to_uom_id)

    def _trigger_uom_warning(self):
        res = super()._trigger_uom_warning()
        if res:
            return res
        so_lines = self.env['sale.order.line'].sudo().search_count(
            [('product_id', 'in', self.ids)], limit=1
        )
        return bool(so_lines)


class ProductAttributeCustomValue(models.Model):
    _inherit = "product.attribute.custom.value"

    sale_order_line_id = fields.Many2one('sale.order.line', string="Sales Order Line", index='btree_not_null', ondelete='cascade')

    _sol_custom_value_unique = models.Constraint(
        'unique(custom_product_template_attribute_value_id, sale_order_line_id)',
        'Only one Custom Value is allowed per Attribute Value per Sales Order Line.',
    )
