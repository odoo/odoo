from odoo import fields, models
from odoo.tools import SQL


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    picking_type_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Warehouse",
        readonly=True,
    )
    date_effective = fields.Datetime(string="Effective Date")
    days_to_arrival = fields.Float(
        string="Effective Days To Arrival",
        digits=(16, 2),
        readonly=True,
        aggregator="avg",
    )

    # ------------------------------------------------------------
    # QUERY METHODS
    # ------------------------------------------------------------

    def _get_select_fields(self) -> dict:
        """Add stock-specific fields to purchase report."""
        fields = super()._get_select_fields()
        fields["picking_type_id"] = "spt.warehouse_id"
        fields["date_effective"] = "o.date_effective"
        fields[
            "days_to_arrival"
        ] = """EXTRACT(
            EPOCH FROM age(
                l.date_planned,
                COALESCE(
                    order_date_effective.date_done,
                    o.date_order
                )
            )
        ) / (24*60*60)::decimal(16,2)"""
        return fields

    def _get_from_tables(self) -> list:
        """Add stock-specific joins to purchase report."""
        tables = super()._get_from_tables()

        # Add stock_picking_type join
        tables.append(
            ("stock_picking_type", "spt", "LEFT JOIN", "spt.id=o.picking_type_id")
        )

        # Add order effective date subquery
        # Note: SQL object already includes the alias in the query
        order_effective_date_subquery = SQL(
            """(
                SELECT MIN(picking.date_done) AS date_done,
                    purchase.id AS purchase_id
                FROM purchase_order AS purchase
                JOIN purchase_order_line AS order_line
                    ON order_line.order_id = purchase.id
                JOIN stock_move AS move
                    ON move.purchase_line_id = order_line.id
                JOIN stock_picking AS picking
                    ON picking.id = move.picking_id
                JOIN stock_location AS location_dest
                    ON location_dest.id = picking.location_dest_id
                WHERE picking.state = 'done'
                    AND location_dest.usage != 'supplier'
                    AND picking.date_done IS NOT NULL
                GROUP BY purchase.id
            ) AS order_date_effective""",
        )

        tables.append(
            (
                order_effective_date_subquery,
                None,  # No alias needed - already in the SQL object
                "LEFT JOIN",
                "order_date_effective.purchase_id = l.order_id",
            ),
        )

        return tables

    def _get_group_by_fields(self) -> list:
        """Add stock-specific fields to GROUP BY clause."""
        fields = super()._get_group_by_fields()
        fields.extend(
            [
                "spt.warehouse_id",
                "o.date_effective",
                "order_date_effective.date_done",
            ],
        )
        return fields
