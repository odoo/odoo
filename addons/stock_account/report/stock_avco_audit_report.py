from odoo import fields, models, tools


class StockAverageCostReport(models.AbstractModel):
    _auto = False
    _name = 'stock.avco.report'
    _description = 'Stock AVCO Justifier'
    _order = 'date desc, id desc'

    date = fields.Date(string='Date', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)

    product_id = fields.Many2one('product.product', string='Product', required=True)

    reference = fields.Char(string='Reference', required=True)
    description = fields.Text(string='Description', required=True)
    type = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
        ('adjustement', 'Adjustement'),
    ], string='Type', required=True)

    res_model_name = fields.Selection([
        ('stock.move', 'Stock Move'),
        ('product.value', 'Product Value'),
    ], string='Resource Model Name', required=True)

    quantity = fields.Float(string='Added Quantity', required=True)
    value = fields.Float(string='Added Value', required=True)

    total_quantity = fields.Float(string='Total Quantity', compute='_compute_cumulative_fields')
    total_value = fields.Float(string='Total Value', compute='_compute_cumulative_fields')
    avco_value = fields.Float(string='AVCO Value', compute='_compute_cumulative_fields')

    def init(self):
        """
        Because we can transfer a product from a warehouse to another one thanks to a stock move, we need to
        generate some fake stock moves before processing all of them. That way, in case of an interwarehouse
        transfer, we will have an outgoing stock move for the source warehouse and an incoming stock move
        for the destination one. To do so, we select all relevant SM (incoming, outgoing and interwarehouse),
        then we duplicate all these SM and edit the values:
            - product_qty is kept if the SM is not the duplicated one or if the SM is an interwarehouse one
                otherwise, we set the value to 0 (this allows us to filter it out during the SM processing)
            - the source warehouse is kept if the SM is not the duplicated one
            - the dest warehouse is kept if the SM is not the duplicated one and is not an interwarehouse
                OR the SM is the duplicated one and is an interwarehouse
        """
        tools.drop_view_if_exists(self.env.cr, 'stock_avco_report')
        query = """
CREATE OR REPLACE VIEW stock_avco_report AS (
SELECT
    sm.id,
    sm.product_id,
    sm.date,
    picking.user_id,
    sm.company_id,
    sm.reference,
    sm.value,
    sm.quantity,
    'stock.move' AS res_model_name,
    'Operation' AS description,
    CASE
        WHEN sm.is_in THEN 'incoming'
        WHEN sm.is_out THEN 'outgoing'
    END AS type
FROM
    stock_move sm
LEFT JOIN
    stock_picking picking ON sm.picking_id = picking.id
LEFT JOIN
    product_product pp ON sm.product_id = pp.id
LEFT JOIN
    product_template pt ON pp.product_tmpl_id = pt.id
LEFT JOIN
    product_category pc ON pt.categ_id = pc.id
LEFT JOIN
    res_company company ON sm.company_id = company.id
WHERE
    sm.state = 'done'
    AND (sm.is_in = TRUE OR sm.is_out = TRUE)
    -- Ignore moves for standard cost method. Only display the list of cost updates
    AND (
        (pt.categ_id IS NOT NULL AND pc.property_cost_method ->> company.id::text IN ('fifo', 'average'))
        OR (pt.categ_id IS NULL AND company.cost_method IN ('fifo', 'average'))
    )
UNION ALL
SELECT
    pv.id,
    pv.product_id,
    pv.date,
    pv.user_id,
    pv.company_id,
    'Adjustment' AS reference, -- Set a fixed string for the reference
    pv.value,
    0 AS quantity, -- Set quantity to 0 as requested,
    'product.value' AS res_model_name,
    pv.description,
    'adjustment' AS type
FROM
    product_value pv
WHERE
    pv.move_id IS NULL
);
"""
        self.env.cr.execute(query)

    def _compute_cumulative_fields(self):
        for records in self.grouped(lambda m: (m.product_id, m.company_id)).values():
            records = records.sorted('date, id')
            total_value = 0.0
            total_quantity = 0.0
            avco = 0.0
            for record in records:
                if record.type == 'incoming':
                    total_value += record.value
                    total_quantity += record.quantity
                    avco = total_value / total_quantity if total_quantity else 0.0
                elif record.type == 'outgoing':
                    total_value -= record.quantity * avco
                    total_quantity -= record.quantity
                elif record.type == 'adjustment':
                    total_value = record.value
                record.total_value = total_value
                record.total_quantity = total_quantity
                record.avco_value = avco
