
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
    reference = fields.Char('Reference')

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_stock_forecast')
        self._cr.execute("""CREATE or REPLACE VIEW report_stock_forecast AS (SELECT
        row_number() OVER (ORDER BY final.date,final.id) AS id,
        product_id as product_id,
        date(final.date) as date,
        sum(product_qty) AS quantity,
        sum(sum(product_qty)) OVER (PARTITION BY final.product_id, final.company_id ORDER BY final.date) AS cumulative_quantity,
        reference,
        final.company_id
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
            location_id.usage = 'internal' or location_id.id is null
            GROUP BY date, product.id, sq.company_id, sq.quantity
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
            GROUP BY sm.date_expected,sm.product_id, sm.company_id, sm.reference
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
            GROUP BY sm.date_expected,sm.product_id, sm.company_id, sm.reference)
         as MAIN
     LEFT JOIN
    (SELECT DISTINCT date
     FROM
     (
            SELECT date_trunc('day', CURRENT_DATE) AS DATE
            UNION ALL
            SELECT date(sm.date_expected) AS date
            FROM stock_move sm
            LEFT JOIN
            stock_location source_location ON sm.location_id = source_location.id
            LEFT JOIN
            stock_location dest_location ON sm.location_dest_id = dest_location.id
            WHERE
            sm.state IN ('confirmed','assigned','waiting') and sm.date_expected > CURRENT_DATE and
            ((dest_location.usage = 'internal' AND source_location.usage != 'internal')
             or (source_location.usage = 'internal' AND dest_location.usage != 'internal'))) AS DATE_SEARCH)
            SUB ON (SUB.date IS NOT NULL)
    GROUP BY MAIN.product_id,SUB.date, MAIN.date, MAIN.company_id,MAIN.reference
    ) AS FINAL
    LEFT JOIN
        stock_picking sp on final.reference=sp.name
    Where final.product_qty != 0 or final.reference = 'Starting Inventory'
    GROUP BY product_id,final.date,final.id,final.company_id,final.reference,sp.priority,sp.date,sp.id)""")

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        orderby = 'date, id' if not orderby else orderby  # Sort result by date_expected and id
        fields.append('quantity') if 'quantity' not in fields else fields
        res = super(ReportStockForecat, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        list_index = []
        lists = []
        qty_for_final_line = []
        cumulative_qty_final_line = []
        res_list = {}
        line_having_id = []
        if 'cumulative_quantity' in fields:
            for line in res:
                if line.get('product_id'):
                    index = res.index(line)
                    if res_list.get(line['product_id']):
                        res_list[line['product_id']].append(line['quantity'])  # Get cumulative quantity product wise
                    else:
                        res_list[line['product_id']] = [line['quantity']]
                    line['cumulative_quantity'] = sum(res_list[line['product_id']])
                    if line.get('reference') == 'Starting Inventory':
                        if line.get('quantity'):
                            line['cumulative_quantity'] = line['quantity']
                        else:
                            if index > 1 and line.get('__count') > 1:
                                line['cumulative_quantity'] = res[index-1]['cumulative_quantity']
                    else:
                        list_index.append(res.index(line)) if not line.get('reference') else list_index
                else:
                    if line.get('quantity'):
                        lists.append(line['quantity'])
                    line['cumulative_quantity'] = sum(lists)
                line_having_id.append(line) if line.get('id') else line_having_id
                if not line.get('reference'):
                    qty_for_final_line.append(line['quantity'])
                    cumulative_qty_final_line.append(line['cumulative_quantity'])
                if line_having_id:
                    line_having_id[0].update({'quantity': sum(qty_for_final_line), 'cumulative_quantity': sum(cumulative_qty_final_line)})
        return res
