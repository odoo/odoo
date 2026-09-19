from odoo import api, fields, models
from odoo.db.schema import drop_view_if_exists
from odoo.fields import Domain

from odoo.addons.stock_account.models.avco import AvcoAccumulator


class StockAverageCostReport(models.AbstractModel):
    _auto = False
    _name = "stock.avco.report"
    _description = "Stock AVCO Justifier"
    _order = "date desc, replay_rank desc, res_id desc"
    _REPLAY_ORDER = "date, replay_rank, res_id"

    date = fields.Datetime(required=True)
    replay_rank = fields.Integer(required=True)
    res_id = fields.Integer(
        string="Resource ID",
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Currency",
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        required=True,
    )

    reference = fields.Char(required=True)
    description = fields.Text(required=True)

    res_model_name = fields.Selection(
        selection=[
            ("stock.move", "Stock Move"),
            ("product.value", "Product Value"),
        ],
        string="Resource Model Name",
        required=True,
    )

    quantity = fields.Float(
        string="Added Quantity",
        required=True,
    )
    value = fields.Float(required=True)

    added_value = fields.Float(compute="_compute_cumulative_fields")
    total_quantity = fields.Float(compute="_compute_cumulative_fields")
    total_value = fields.Float(compute="_compute_cumulative_fields")
    avco_value = fields.Float(
        string="AVCO Value",
        compute="_compute_cumulative_fields",
    )

    justification = fields.Text(compute="_compute_justification")

    def init(self):
        drop_view_if_exists(self.env.cr, "stock_avco_report")
        query = """
CREATE OR REPLACE VIEW stock_avco_report AS (
SELECT
    sm.id AS id,
    sm.id AS res_id,
    0 AS replay_rank,
    sm.product_id,
    sm.date,
    picking.user_id,
    sm.company_id,
    sm.reference,
    CASE WHEN sm.is_in THEN sm.value ELSE -sm.value END AS value,
    -- `valued_qty`, not `quantity`: the engine feeds the accumulator
    -- `_get_valued_qty()` -- picked, company-owned lines only -- while
    -- `stock_move.quantity` sums every line. A receipt of 10 owned plus 5
    -- consigned units made this report justify an average cost of 6.67 against a
    -- product actually valued at 10.00. `valued_qty` is the stored record of the
    -- quantity `value` was computed over, so the two cannot drift again; it is
    -- already in the product's UoM, which is why the uom_uom joins are gone.
    CASE WHEN sm.is_in THEN sm.valued_qty ELSE -sm.valued_qty END AS quantity,
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
    -- Dropship moves are deliberately absent: `_run_average_batch` replays them
    -- as an `add_in` immediately followed by an `add_out` at the same cost, so
    -- they move neither the quantity nor the average, and a single row could
    -- only misrepresent one half of that pair.
    AND (sm.is_in = TRUE OR sm.is_out = TRUE)
    -- Ignore moves valued at standard cost; for those only the cost updates matter.
    -- The effective method is the category's company-dependent value, falling back to
    -- the company default. Spelled as COALESCE because the equivalent OR-chain binds
    -- AND tighter than OR, which silently let every category-less product through.
    AND COALESCE(
        pc.property_cost_method ->> company.id::text,
        company.cost_method
    ) IN ('fifo', 'average')
UNION ALL
SELECT
    -pv.id,
    pv.id AS res_id,
    1 AS replay_rank,
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
    -- Match `_get_last_product_value`, which seeds the product-wide replay from
    -- `lot_id = False` rows only. A lot revaluation used to surface here as a
    -- product-wide `set_unit_cost` the engine had never applied.
    AND pv.lot_id IS NULL
);
"""
        self.env.cr.execute(query)

    # The override flushes and delegates; it reads nothing the domain does not.
    _search_visibility_fields = ()

    def _search(self, domain, *args, **kwargs):
        self.env.flush_all()
        return super()._search(domain, *args, **kwargs)

    @api.depends(
        "value",
        "quantity",
        "date",
        "product_id.stock_move_ids.value",
        "product_id.stock_move_ids.valued_qty",
        "product_id.stock_move_ids.is_in",
        "product_id.stock_move_ids.is_out",
    )
    def _compute_cumulative_fields(self):
        pages_by_key = self.grouped(lambda m: (m.product_id, m.company_id))
        total_records_grouped = (
            self.env["stock.avco.report"]
            .search(
                Domain.OR(
                    Domain(
                        [
                            ("product_id", "=", product.id),
                            ("company_id", "=", company.id),
                        ]
                    )
                    for product, company in pages_by_key
                )
                if pages_by_key
                else Domain.FALSE
            )
            .grouped(lambda m: (m.product_id, m.company_id))
        )
        for key, records in pages_by_key.items():
            current_page_ids = set(records.ids)
            total_records = total_records_grouped.get(key, self.browse()).sorted(
                self._REPLAY_ORDER
            )
            avco = AvcoAccumulator(uom=records.product_id.uom_id)
            added_value = 0.0
            for record in total_records:
                if record.res_model_name == "stock.move":
                    if record.quantity > 0:
                        added_value = avco.add_in(record.quantity, record.value)
                    else:
                        added_value = -avco.add_out(-record.quantity)
                elif record.res_model_name == "product.value":
                    added_value = avco.set_unit_cost(record.value)

                if record.id in current_page_ids:
                    record.added_value = added_value
                    record.total_value = avco.value
                    record.total_quantity = avco.quantity
                    record.avco_value = avco.unit_cost

    @api.depends("res_id", "res_model_name")
    def _compute_justification(self):
        self.justification = False
        for record in self:
            if record.res_model_name == "stock.move":
                record.justification = (
                    self.env["stock.move"].browse(record.res_id).value_justification
                )
