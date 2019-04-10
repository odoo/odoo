# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools


class ReportStockForecat(models.Model):
    _name = 'report.stock.forecast'
    _auto = False
    _description = 'Stock Forecast Report'

    date = fields.Date(string='Date')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id', readonly=True)
    cumulative_quantity = fields.Float(string='Cumulative Quantity', readonly=True)
    quantity = fields.Float(readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Picking', readonly=True)
    reference = fields.Char('Reference')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_stock_forecast')
        query = """
        CREATE or REPLACE VIEW report_stock_forecast AS (SELECT
            %s
        FROM
            (SELECT
                MIN(id) as id,
                MAIN.product_id as product_id,
                date(SUB.date) as date,
                CASE WHEN MAIN.date = SUB.date THEN sum(MAIN.product_qty) ELSE 0 END as product_qty,
                MAIN.reference as reference,
                MAIN.company_id as company_id
            FROM
                (SELECT
                    MIN(-product.id) as id,
                    product.id as product_id,
                    date(CURRENT_DATE) as date,
                    SUM(sq.quantity) AS product_qty,
                    'Starting Inventory' as reference,
                    sq.company_id
                FROM
                    product_product as product
                LEFT JOIN
                    stock_quant sq ON product.id = sq.product_id
                LEFT JOIN
                    stock_location location_id ON sq.location_id = location_id.id
                WHERE
                    location_id.usage = 'internal'
                GROUP BY
                    date, product.id, sq.company_id, sq.quantity
                UNION ALL
                SELECT
                    MIN(sm.id) as id,
                    sm.product_id,
                    CASE WHEN sm.date_expected > CURRENT_DATE
                    THEN date(sm.date_expected)
                    ELSE date(CURRENT_DATE) END
                    AS date,
                    SUM(sm.product_qty) AS product_qty,
                    sm.reference as reference,
                    sm.company_id
                FROM
                    stock_move as sm
                LEFT JOIN
                   product_product ON product_product.id = sm.product_id
                LEFT JOIN
                    stock_location dest_location ON sm.location_dest_id = dest_location.id
                LEFT JOIN
                    stock_location source_location ON sm.location_id = source_location.id
                WHERE
                    sm.state IN ('confirmed','partially_available','assigned','waiting') and
                    source_location.usage != 'internal' and dest_location.usage = 'internal'
                GROUP BY
                    sm.date_expected,sm.product_id, sm.company_id, sm.reference
                UNION ALL
                SELECT
                    MIN(sm.id) as id,
                    sm.product_id,
                    CASE WHEN sm.date_expected > CURRENT_DATE
                        THEN date(sm.date_expected)
                        ELSE date(CURRENT_DATE) END
                    AS date,
                    SUM(-(sm.product_qty)) AS product_qty,
                    sm.reference AS reference,
                    sm.company_id
                FROM
                   stock_move as sm
                LEFT JOIN
                   product_product ON product_product.id = sm.product_id
                LEFT JOIN
                   stock_location source_location ON sm.location_id = source_location.id
                LEFT JOIN
                   stock_location dest_location ON sm.location_dest_id = dest_location.id
                WHERE
                    sm.state IN ('confirmed','partially_available','assigned','waiting') and
                    source_location.usage = 'internal' and dest_location.usage != 'internal'
                GROUP BY
                    sm.date_expected,sm.product_id, sm.company_id, sm.reference
                ) AS MAIN
            LEFT JOIN
                (SELECT
                    DISTINCT date
                 FROM
                    (SELECT
                        date_trunc('day', CURRENT_DATE) AS DATE
                    UNION ALL
                    SELECT
                        date(sm.date_expected) AS date
                    FROM
                        stock_move sm
                    LEFT JOIN
                        stock_location source_location ON sm.location_id = source_location.id
                    LEFT JOIN
                        stock_location dest_location ON sm.location_dest_id = dest_location.id
                    WHERE
                        sm.state IN ('confirmed','assigned','waiting') AND
                        sm.date_expected > CURRENT_DATE AND
                        ((dest_location.usage = 'internal' AND
                        source_location.usage != 'internal') OR
                        (source_location.usage = 'internal' AND
                        dest_location.usage != 'internal'))
                    ) AS DATE_SEARCH
                ) AS SUB ON SUB.date IS NOT NULL
            GROUP BY
                MAIN.product_id,SUB.date, MAIN.date, MAIN.company_id,MAIN.reference
            ) AS FINAL
        %s
        WHERE
            final.product_qty != 0 OR final.reference = 'Starting Inventory'
        %s
        ORDER BY
            date
        )
        """ % (self._select(), self._left_join(), self._groupby())
        self.env.cr.execute(query)

    @api.model
    def _select(self):
        return """
            row_number() OVER (ORDER BY final.date,final.id) AS id,
            final.product_id as product_id,
            date(final.date) as date,
            sum(final.product_qty) AS quantity,
            sum(sum(final.product_qty)) OVER (PARTITION BY final.product_id, final.company_id ORDER BY final.date) AS cumulative_quantity,
            reference,
            sp.id as picking_id,
            final.company_id
        """

    @api.model
    def _left_join(self):
        return """LEFT JOIN
            stock_picking sp ON final.reference=sp.name
        """

    @api.model
    def _groupby(self):
        return """GROUP BY
            final.product_id,
            final.date,
            final.id,
            final.company_id,
            final.reference,
            sp.priority,
            sp.date,
            sp.id
        """

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ Override read_group in order to display the correct cumulative
        quantity. The cumulative quantity for a group of moves/quants
        should be the last for the selected time interval (given by domain).
        However select the 'last' record's value in a groupby is not possible
        (only possible aggregation functions are the ones provided by
        PostgreSQL). The cumulative quantity is recomputed since a search on
        each group returned by the super would consume too much time. The
        cumulative quantity is computed based on previous group.
        - Group1: sum of the quantity of records in group1.
        - Group2: cumulative_quantity of group1 + sum of quantity of records in group2
        - Group3: cumulative_quantity of group2 + sum of quantity of records in group3
        ...
        Since read_group depends on domain, some records could be excluded and
        the computed cumulative quantity could be different than the one computed
        in SQL. It's wanted since the customer could play with the domain in
        order to analyze different quantities in different situations.
        """
        # Sort result by date_expected and id.
        if 'cumulative_quantity' in fields and 'quantity' not in fields:
            fields.append('quantity')
        res = super(ReportStockForecat, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        total_cumulative_quantity = 0
        cumulative_quantity_by_products = {}
        if 'cumulative_quantity' in fields:
            for index, line in enumerate(res):
                # If the stock forecast cell have a 0 quantity the read_group
                # will not return their sum as 0 but False.
                if 'quantity' in line and not line['quantity']:
                    line['quantity'] = 0.0
                if line.get('product_id'):
                    product_id = line['product_id']
                    if not cumulative_quantity_by_products.get(product_id):
                        cumulative_quantity_by_products[product_id] = 0
                    cumulative_quantity_by_products[product_id] += line['quantity']  # Get cumulative quantity product wise
                    line['cumulative_quantity'] = cumulative_quantity_by_products[product_id]  # Sum of all quantities (i.e. cumulative quantity) product wise
                elif line.get('reference'):
                    if line['reference'] == 'Starting Inventory':
                        if index == 0:
                            line['cumulative_quantity'] = line['quantity']
                        else:
                            line['quantity'] = 0.0
                            line['cumulative_quantity'] = res[index - 1]['cumulative_quantity']  # Set cumulatiove quantity if line does not have any cumulative
                elif line.get('quantity', False):
                    total_cumulative_quantity += line['quantity']
                    line['cumulative_quantity'] = total_cumulative_quantity  # Sum of all Move Operations' quantity
                else:
                    line['cumulative_quantity'] = 0
        return res
