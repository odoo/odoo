# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.osv import expression


class LunchProductReport(models.Model):
    _name = "lunch.product.report"
    _description = 'Product report'
    _auto = False
    _order = 'is_favorite desc, is_new desc, last_order_date asc, product_id asc'

    id = fields.Integer('ID')
    product_id = fields.Integer('Product ID')
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

    # This field is used only for searching
    is_available_at = fields.Many2one('lunch.location', 'Product Availability', compute='_compute_is_available_at', search='_search_is_available_at')

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
        user_id = self.env.user.id
        if 'is_favorite' in values:
            for report in self:
                if values['is_favorite']:
                    self.env.cr.execute('''INSERT INTO lunch_product_favorite_user_rel(product_id, user_id) VALUES (%s, %s)''',
                                (report.product_id, user_id))
                else:
                    self.env.cr.execute('''DELETE FROM lunch_product_favorite_user_rel WHERE product_id=%s AND user_id=%s''',
                                (report.product_id, user_id))

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)

        self._cr.execute("""
            CREATE or REPLACE view %s AS (
                SELECT
                    row_number() over (ORDER BY user_id,product.id) AS id,
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
                INNER JOIN res_users users ON users.company_id = product.company_id -- multi company
                INNER JOIN res_groups_users_rel groups ON groups.uid = users.id -- only generate for internal users
                LEFT JOIN LATERAL (select max(date) AS last_order_date FROM lunch_order where user_id=users.id and product_id=product.id) AS orders ON TRUE
                LEFT JOIN LATERAL (select user_id FROM lunch_product_favorite_user_rel where user_id=users.id and product_id=product.id) AS fav ON TRUE
                WHERE users.active AND product.active AND groups.gid = %%s --only take into account active products and users
            );
        """ % self._table, (self.env.ref('base.group_user').id,))
