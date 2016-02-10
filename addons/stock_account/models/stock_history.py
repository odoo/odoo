# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.fields import datetime


class StockHistory(models.Model):
    _name = 'stock.history'
    _auto = False
    _order = 'date'

    move_id = fields.Many2one('stock.move', 'Stock Move', required=True)
    location_id = fields.Many2one('stock.location', 'Location', required=True)
    company_id = fields.Many2one('res.company', 'Company')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_categ_id = fields.Many2one('product.category', 'Product Category', required=True)
    quantity = fields.Float('Product Quantity')
    date = fields.Datetime('Operation Date')
    price_unit_on_quant = fields.Float('Value')
    inventory_value=  fields.Float(compute='_get_inventory_value', string="Inventory Value", readonly=True)
    source = fields.Char()
    product_template_id = fields.Many2one('product.template', 'Product Template', required=True)
    serial_number = fields.Char('Serial Number', required=True)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(StockHistory, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        StockHistories = self.env['stock.history']
        history_date = self.env.context.get('history_date', datetime.now())
        if 'inventory_value' in fields:
            group_lines = {}
            for line in res:
                domain = line.get('__domain', domain)
                histories = self.search(domain)
                group_lines.setdefault(str(domain), histories)
                StockHistories |= histories

            cost_method_product_ids = StockHistories.mapped('product_id').filtered(lambda p: p.cost_method != 'real').ids
            prod_price_histories = self.env['product.price.history'].search([('product_id', 'in', cost_method_product_ids), ('datetime', '<=', history_date)])

            prod_price_histories_dict = dict([((prod_history.product_id, prod_history.company_id), prod_history.cost) for prod_history in prod_price_histories])

            for line in res:
                inv_value = 0.0
                histories = group_lines.get(str(line.get('__domain', domain)))
                for history in histories:
                    if history.product_id.cost_method == 'real':
                        price = history.price_unit_on_quant
                    else:
                        price = prod_price_histories_dict.get((history.product_id, history.company_id), 0.0)
                    inv_value += price * history.quantity
                line['inventory_value'] = inv_value
        return res

    def _get_inventory_value(self):
        history_date = self.env.context.get('history_date')
        Product = self.env["product.product"]
        for line in self:
            if line.product_id.cost_method == 'real':
                line.inventory_value = line.quantity * line.price_unit_on_quant
            else:
                line.inventory_value = line.quantity * Product.get_history_price(line.product_id.id, line.company_id.id, date=history_date)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'stock_history')
        cr.execute("""
            CREATE OR REPLACE VIEW stock_history AS (
              SELECT MIN(id) as id,
                move_id,
                location_id,
                company_id,
                product_id,
                product_categ_id,
                product_template_id,
                SUM(quantity) as quantity,
                date,
                price_unit_on_quant,
                source,
                serial_number
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
                    (source_location.company_id is null and dest_location.company_id is not null) or
                    (source_location.company_id is not null and dest_location.company_id is null) or
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
                    (dest_location.company_id is null and source_location.company_id is not null) or
                    (dest_location.company_id is not null and source_location.company_id is null) or
                    dest_location.company_id != source_location.company_id or
                    dest_location.usage not in ('internal', 'transit'))
                ))
                AS foo
                GROUP BY move_id, location_id, company_id, product_id, product_categ_id, date, price_unit_on_quant, source, product_template_id, serial_number
            )""")
