# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools
from odoo.osv import expression


class LunchProductReport(models.Model):
    _name = "lunch.product.report"
    _description = 'Product report'
    _auto = False
    _order = 'is_favorite desc, is_new desc, last_order_date asc, product_id asc'

    id = fields.Integer('ID')
    product_id = fields.Many2one('lunch.product', 'Product')
    name = fields.Char('Product Name')
    category_id = fields.Many2one('lunch.product.category', 'Product Category')
    description = fields.Text('Description')
    price = fields.Float('Price')
    supplier_id = fields.Many2one('lunch.supplier', 'Vendor')
    company_id = fields.Many2one('res.company')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    is_favorite = fields.Boolean('Favorite')
    user_id = fields.Many2one('res.users')
    is_new = fields.Boolean('New')
    active = fields.Boolean('Active')
    last_order_date = fields.Date('Last Order Date')
    image_128 = fields.Image(compute="_compute_image_128")

    # This field is used only for searching
    is_available_at = fields.Many2one('lunch.location', 'Product Availability', compute='_compute_is_available_at', search='_search_is_available_at')

    def _compute_image_128(self):
        for product_r in self:
            product = product_r.product_id
            category = product_r.category_id
            if product.image_128:
                product_r.image_128 = product.image_128
            elif category.image_128:
                product_r.image_128 = category.image_128
            else:
                product_r.image_128 = False

    def _compute_is_available_at(self):
        """
            Is available_at is always false when browsing it
            this field is there only to search (see _search_is_available_at)
        """
        for product in self:
            product.is_available_at = False

    def _search_is_available_at(self, operator, value):
        supported_operators = ['in', 'not in', '=', '!=']

        if not operator in supported_operators:
            return expression.TRUE_DOMAIN

        if isinstance(value, int):
            value = [value]

        if operator in expression.NEGATIVE_TERM_OPERATORS:
            return expression.AND([[('supplier_id.available_location_ids', 'not in', value)], [('supplier_id.available_location_ids', '!=', False)]])

        return expression.OR([[('supplier_id.available_location_ids', 'in', value)], [('supplier_id.available_location_ids', '=', False)]])

    def write(self, values):
        if 'is_favorite' in values:
            if values['is_favorite']:
                commands = [(4, product_id) for product_id in self.mapped('product_id').ids]
            else:
                commands = [(3, product_id) for product_id in self.mapped('product_id').ids]
            self.env.user.write({
                'favorite_lunch_product_ids': commands,
            })

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)

        self._cr.execute("""
            CREATE or REPLACE view %s AS (
                SELECT
                    row_number() over (ORDER BY users.id,product.id) AS id,
                    product.id AS product_id,
                    product.name,
                    product.category_id,
                    product.description,
                    product.price,
                    product.supplier_id,
                    product.company_id,
                    product.active,
                    users.id AS user_id,
                    fav.user_id IS NOT NULL AS is_favorite,
                    product.new_until >= current_date AS is_new,
                    orders.last_order_date
                FROM lunch_product product
                INNER JOIN res_users users ON product.company_id IS NULL OR users.company_id = product.company_id -- multi company
                INNER JOIN res_groups_users_rel groups ON groups.uid = users.id -- only generate for internal users
                LEFT JOIN LATERAL (select max(date) AS last_order_date FROM lunch_order where user_id=users.id and product_id=product.id) AS orders ON TRUE
                LEFT JOIN LATERAL (select user_id FROM lunch_product_favorite_user_rel where user_id=users.id and product_id=product.id) AS fav ON TRUE
                WHERE users.active AND product.active AND groups.gid = %%s --only take into account active products and users
            );
        """ % self._table, (self.env.ref('base.group_user').id,))
