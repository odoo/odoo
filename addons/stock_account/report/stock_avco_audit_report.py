from odoo import fields, models, tools


class StockAverageCostReport(models.AbstractModel):
    _auto = False
    _name = 'stock.avco.report'
    _description = 'Stock AVCO Justifier'
    _order = 'date desc, id desc'

    date = fields.Date(string='Date', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')

    product_id = fields.Many2one('product.product', string='Product', required=True)

    reference = fields.Char(string='Reference', required=True)
    description = fields.Text(string='Description', required=True)

    res_model_name = fields.Selection([
        ('stock.move', 'Stock Move'),
        ('product.value', 'Product Value'),
    ], string='Resource Model Name', required=True)

    quantity = fields.Float(string='Added Quantity', required=True)
    value = fields.Float(string='Value', required=True)

    added_value = fields.Float(string='Added Value', compute='_compute_cumulative_fields')
    total_quantity = fields.Float(string='Total Quantity', compute='_compute_cumulative_fields')
    total_value = fields.Float(string='Total Value', compute='_compute_cumulative_fields')
    avco_value = fields.Float(string='AVCO Value', compute='_compute_cumulative_fields')

    justification = fields.Text(string='Justification', compute='_compute_justification')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'stock_avco_report')
        query = """
CREATE OR REPLACE VIEW stock_avco_report AS (
SELECT
    sm.id AS id,
    sm.product_id,
    sm.date,
    picking.user_id,
    sm.company_id,
    sm.reference,
    CASE WHEN sm.is_in THEN sm.value ELSE -sm.value END AS value,
    CASE WHEN sm.is_in THEN sm.quantity ELSE -sm.quantity END AS quantity,
    'stock.move' AS res_model_name,
    'Operation' AS description
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
        OR (pt.categ_id IS NULL OR (pc.property_cost_method IS NULL OR pc.property_cost_method ->> company.id::text IS NULL) AND company.cost_method IN ('fifo', 'average'))
    )
UNION ALL
SELECT
    -pv.id,
    pv.product_id,
    pv.date,
    pv.user_id,
    pv.company_id,
    'Adjustment' AS reference, -- Set a fixed string for the reference
    pv.value,
    0 AS quantity, -- Set quantity to 0 as requested,
    'product.value' AS res_model_name,
    pv.description
FROM
    product_value pv
WHERE
    pv.move_id IS NULL
);
"""
        self.env.cr.execute(query)

    def _compute_cumulative_fields(self):
        total_records_grouped = self.env['stock.avco.report'].search(
            [('product_id', 'in', self.product_id.mapped('id')), ('company_id', 'in', self.company_id.mapped('id'))]
        ).grouped(lambda m: (m.product_id, m.company_id))
        for records in self.grouped(lambda m: (m.product_id, m.company_id)).values():
            current_page_records = records.sorted('date, id')
            total_records = total_records_grouped.get((records.product_id, records.company_id)).sorted('date, id')
            added_value = 0.0
            total_value = 0.0
            total_quantity = 0.0
            avco = 0.0
            for record in total_records:
                if record.res_model_name == 'stock.move':
                    if record.quantity > 0:
                        added_value = record.value
                    elif record.quantity < 0:
                        added_value = avco * record.quantity
                    total_value += added_value
                    total_quantity += record.quantity

                elif record.res_model_name == 'product.value':
                    added_value = (record.value * total_quantity) - total_value
                    total_value = record.value * total_quantity

                if total_quantity:
                    avco = total_value / total_quantity
                if record in current_page_records:
                    record.added_value = added_value
                    record.total_value = total_value
                    record.total_quantity = total_quantity
                    record.avco_value = avco

    def _compute_justification(self):
        self.justification = False
        for record in self:
            if record.res_model_name == 'stock.move':
                record.justification = self.env['stock.move'].browse(record.id).value_justification
