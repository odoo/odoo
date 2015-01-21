from openerp import fields, models
from openerp import tools

class report_stock_forecast(models.Model):
    _name = 'report.stock.forecast'
    _auto = False

    date = fields.Date(readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    cumulative_quantity = fields.Float(string='Cumulative Quantity', readonly=True)
    quantity = fields.Float(readonly=True)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_stock_forecast')
        cr.execute("""CREATE or REPLACE VIEW report_stock_forecast AS (SELECT
                        max(id) AS id,
                        product_id,
                        date,
                        sum(product_qty) as quantity,
                        sum(sum(product_qty)) OVER(PARTITION BY product_id ORDER BY date) AS cumulative_quantity
                        FROM (
                            SELECT
                                max(sq.id) AS id,
                                sq.product_id,
                                CURRENT_DATE AS date,
                                sum(sq.qty) AS product_qty
                            FROM
                               stock_quant as sq
                            LEFT JOIN
                               product_product ON product_product.id = sq.product_id
                            LEFT JOIN
                                stock_location location_id ON sq.location_id = location_id.id
                            WHERE
                                location_id.usage = 'internal'
                            GROUP BY
                                CURRENT_DATE,
                                sq.product_id
                            UNION ALL
                            SELECT
                                max(sm.id) AS id,
                                sm.product_id,
                                to_date(to_char(sm.date, 'YYYY/MM/DD'), 'YYYY/MM/DD') AS date,
                                sum(sm.product_qty) AS product_qty
                            FROM
                               stock_move as sm
                            LEFT JOIN
                               product_product ON product_product.id = sm.product_id
                            LEFT JOIN
                                stock_location dest_location ON sm.location_dest_id = dest_location.id
                            LEFT JOIN
                                stock_location source_location ON sm.location_id = source_location.id
                            WHERE
                                sm.state IN ('confirmed','assigned','waiting') and
                                source_location.usage != 'internal' and dest_location.usage = 'internal'
                            GROUP BY
                                to_date(to_char(sm.date, 'YYYY/MM/DD'), 'YYYY/MM/DD'),
                                sm.product_id
                            UNION ALL
                            SELECT
                                max(sm.id) AS id,
                                sm.product_id,
                                to_date(to_char(sm.date, 'YYYY/MM/DD'), 'YYYY/MM/DD') AS date,
                                -sum(sm.product_qty) AS product_qty
                            FROM
                               stock_move as sm
                            LEFT JOIN
                               product_product ON product_product.id = sm.product_id
                            LEFT JOIN
                               stock_location source_location ON sm.location_id = source_location.id
                            LEFT JOIN
                               stock_location dest_location ON sm.location_dest_id = dest_location.id
                            WHERE
                                sm.state IN ('confirmed','assigned','waiting') and
                            source_location.usage = 'internal' and dest_location.usage != 'internal'
                            GROUP BY
                                to_date(to_char(sm.date, 'YYYY/MM/DD'), 'YYYY/MM/DD'),
                                sm.product_id
                            ) as report
                        GROUP BY date,product_id)""")
