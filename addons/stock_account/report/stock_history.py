# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.fields import Datetime as fieldsDatetime


class StockHistory(models.Model):
    _name = 'stock.history'
    _auto = False
    _order = 'date asc'

    move_id = fields.Many2one('stock.move', 'Stock Move', required=True)
    location_id = fields.Many2one('stock.location', 'Location', required=True)
    company_id = fields.Many2one('res.company', 'Company')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_categ_id = fields.Many2one('product.category', 'Product Category', required=True)
    quantity = fields.Float('Product Quantity')
    date = fields.Datetime('Operation Date')
    price_unit_on_quant = fields.Float('Value')
    inventory_value = fields.Float('Inventory Value', compute='_compute_inventory_value', readonly=True)
    source = fields.Char('Source')
    product_template_id = fields.Many2one('product.template', 'Product Template', required=True)
    serial_number = fields.Char('Lot/Serial Number', required=True)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(StockHistory, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        if 'inventory_value' in fields:
            date = self._context.get('history_date', fieldsDatetime.now())
            stock_history = self.env['stock.history']
            group_lines = {}
            for line in res:
                domain = line.get('__domain', domain)
                group_lines.setdefault(str(domain), self.search(domain))
                stock_history |= group_lines[str(domain)]

            histories_dict = {}
            not_real_cost_method_products = stock_history.mapped('product_id').filtered(lambda product: product.cost_method != 'real')
            if not_real_cost_method_products:
                self._cr.execute("""SELECT DISTINCT ON (product_id, company_id) product_id, company_id, cost
                    FROM product_price_history
                    WHERE product_id in %s AND datetime <= %s
                    ORDER BY product_id, company_id, datetime DESC, id DESC""", (tuple(not_real_cost_method_products.ids), date))
                for history in self._cr.dictfetchall():
                    histories_dict[(history['product_id'], history['company_id'])] = history['cost']

            for line in res:
                inv_value = 0.0
                for stock_history in group_lines.get(str(line.get('__domain', domain))):
                    product = stock_history.product_id
                    if product.cost_method == 'real':
                        price = stock_history.price_unit_on_quant
                    else:
                        price = histories_dict.get((product.id, stock_history.company_id.id), 0.0)
                    inv_value += price * stock_history.quantity
                line['inventory_value'] = inv_value

        return res

    @api.one
    def _compute_inventory_value(self):
        if self.product_id.cost_method == 'real':
            self.inventory_value = self.quantity * self.price_unit_on_quant
        else:
            self.inventory_value = self.quantity * self.product_id.get_history_price(self.company_id.id, date=self._context.get('history_date', fields.Datetime.now()))

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'stock_history')
        self._cr.execute("""
            CREATE VIEW stock_history AS (
              SELECT MIN(id) as id,
                move_id,
                location_id,
                company_id,
                product_id,
                product_categ_id,
                product_template_id,
                SUM(quantity) as quantity,
                date,
                COALESCE(SUM(price_unit_on_quant * quantity) / NULLIF(SUM(quantity), 0), 0) as price_unit_on_quant,
                source,
                string_agg(DISTINCT serial_number, ', ' ORDER BY serial_number) AS serial_number
                FROM
                ((SELECT
                    stock_move.id AS id,
                    stock_move.id AS move_id,
                    dest_location.id AS location_id,
                    dest_location.company_id AS company_id,
                    stock_move.product_id AS product_id,
                    product_template.id AS product_template_id,
                    product_template.categ_id AS product_categ_id,
                    quant.qty AS quantity,
                    stock_move.date AS date,
                    quant.cost as price_unit_on_quant,
                    stock_move.origin AS source,
                    stock_production_lot.name AS serial_number
                FROM
                    stock_quant as quant
                JOIN
                    stock_quant_move_rel ON stock_quant_move_rel.quant_id = quant.id
                JOIN
                    stock_move ON stock_move.id = stock_quant_move_rel.move_id
                LEFT JOIN
                    stock_production_lot ON stock_production_lot.id = quant.lot_id
                JOIN
                    stock_location dest_location ON stock_move.location_dest_id = dest_location.id
                JOIN
                    stock_location source_location ON stock_move.location_id = source_location.id
                JOIN
                    product_product ON product_product.id = stock_move.product_id
                JOIN
                    product_template ON product_template.id = product_product.product_tmpl_id
                WHERE quant.qty>0 AND stock_move.state = 'done' AND dest_location.usage in ('internal', 'transit')
                AND (
                    not (source_location.company_id is null and dest_location.company_id is null) or
                    source_location.company_id != dest_location.company_id or
                    source_location.usage not in ('internal', 'transit'))
                ) UNION ALL
                (SELECT
                    (-1) * stock_move.id AS id,
                    stock_move.id AS move_id,
                    source_location.id AS location_id,
                    source_location.company_id AS company_id,
                    stock_move.product_id AS product_id,
                    product_template.id AS product_template_id,
                    product_template.categ_id AS product_categ_id,
                    - quant.qty AS quantity,
                    stock_move.date AS date,
                    quant.cost as price_unit_on_quant,
                    stock_move.origin AS source,
                    stock_production_lot.name AS serial_number
                FROM
                    stock_quant as quant
                JOIN
                    stock_quant_move_rel ON stock_quant_move_rel.quant_id = quant.id
                JOIN
                    stock_move ON stock_move.id = stock_quant_move_rel.move_id
                LEFT JOIN
                    stock_production_lot ON stock_production_lot.id = quant.lot_id
                JOIN
                    stock_location source_location ON stock_move.location_id = source_location.id
                JOIN
                    stock_location dest_location ON stock_move.location_dest_id = dest_location.id
                JOIN
                    product_product ON product_product.id = stock_move.product_id
                JOIN
                    product_template ON product_template.id = product_product.product_tmpl_id
                WHERE quant.qty>0 AND stock_move.state = 'done' AND source_location.usage in ('internal', 'transit')
                AND (
                    not (dest_location.company_id is null and source_location.company_id is null) or
                    dest_location.company_id != source_location.company_id or
                    dest_location.usage not in ('internal', 'transit'))
                ))
                AS foo
                GROUP BY move_id, location_id, company_id, product_id, product_categ_id, date, source, product_template_id
            )""")
