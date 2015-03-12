# -*- coding: utf-8 -*-


from openerp import fields, models
from openerp import tools


class report_stock_forecast(models.Model):
    _name = 'report.stock.forecast'
    _auto = False

    date = fields.Date(string='Date')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    cumulative_quantity = fields.Float(string='Cumulative Quantity', readonly=True)
    quantity = fields.Float(readonly=True)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_stock_forecast')
        cr.execute("""CREATE or REPLACE VIEW report_stock_forecast AS (SELECT
        max(id) as id,
        product_id as product_id,
        date as date,
        sum(product_qty) AS quantity,
        sum(sum(product_qty)) OVER(PARTITION BY product_id ORDER BY date ) AS cumulative_quantity
        FROM
        (SELECT
        max(id) as id,
        MAIN.product_id as product_id,
        SUB.date as date,
        CASE WHEN MAIN.date = SUB.date THEN sum(MAIN.product_qty) ELSE 0 END as product_qty
        FROM
        (SELECT
            max(sq.id) as id,
            sq.product_id,
            CASE WHEN sm.date < CURRENT_DATE
            THEN to_date(to_char(sm.date, 'YYYY/MM/DD'), 'YYYY/MM/DD')
            ELSE to_date(to_char(CURRENT_DATE, 'YYYY/MM/DD'), 'YYYY/MM/DD')
            END AS date,
            SUM(sq.qty) AS product_qty
            FROM
            (SELECT min(date) AS date FROM stock_move AS sm
                LEFT JOIN
                    stock_location source_location ON sm.location_id = source_location.id
                LEFT JOIN
                    stock_location dest_location ON sm.location_dest_id = dest_location.id
                WHERE
                    sm.state IN ('confirmed','assigned','waiting') AND
                    (dest_location.usage = 'internal' AND source_location.usage != 'internal')
                        or (source_location.usage = 'internal' AND dest_location.usage != 'internal')) AS sm,
            stock_quant as sq
            LEFT JOIN
            product_product ON product_product.id = sq.product_id
            LEFT JOIN
            stock_location location_id ON sq.location_id = location_id.id
            WHERE
            location_id.usage = 'internal'
            GROUP BY date, sq.product_id
            UNION ALL
            SELECT
            max(sm.id) as id,
            sm.product_id,
            to_date(to_char(sm.date, 'YYYY/MM/DD'), 'YYYY/MM/DD') AS date,
            SUM(sm.product_qty) AS product_qty
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
            GROUP BY sm.date,sm.product_id
            UNION ALL
            SELECT
                max(sm.id) as id,
                sm.product_id,
                to_date(to_char(sm.date, 'YYYY/MM/DD'), 'YYYY/MM/DD') AS date,
                SUM(-(sm.product_qty)) AS product_qty
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
            GROUP BY sm.date,sm.product_id)
         as MAIN
     LEFT JOIN
     (SELECT DISTINCT date
      FROM
      (
             SELECT CURRENT_DATE AS DATE
             UNION ALL
             SELECT to_date(to_char(sm.date, 'YYYY/MM/DD'), 'YYYY/MM/DD') AS date
             FROM stock_move sm
             LEFT JOIN
             stock_location source_location ON sm.location_id = source_location.id
             LEFT JOIN
             stock_location dest_location ON sm.location_dest_id = dest_location.id
             WHERE
             sm.state IN ('confirmed','assigned','waiting') and
             (dest_location.usage = 'internal' AND source_location.usage != 'internal')
              or (source_location.usage = 'internal' AND dest_location.usage != 'internal')) AS DATE_SEARCH)
             SUB ON (SUB.date IS NOT NULL)
    GROUP BY MAIN.product_id,SUB.date, MAIN.date
    ) AS FINAL
    GROUP BY product_id,date)""")
