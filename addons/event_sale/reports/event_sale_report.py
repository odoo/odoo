from odoo import fields, models
from odoo.db.schema import drop_view_if_exists

from odoo.addons.sale import const


class EventSaleReport(models.Model):
    """Event Registrations-based sales report."""

    _name = "event.sale.report"
    _description = "Event Sales Report"
    _auto = False
    _rec_name = "sale_order_line_id"

    event_type_id = fields.Many2one(
        comodel_name="event.type",
        readonly=True,
    )
    event_id = fields.Many2one(
        comodel_name="event.event",
        readonly=True,
    )
    event_date_begin = fields.Date(
        string="Event Start Date",
        readonly=True,
    )
    event_date_end = fields.Date(
        string="Event End Date",
        readonly=True,
    )
    event_slot_id = fields.Many2one(
        comodel_name="event.slot",
        readonly=True,
    )
    event_ticket_id = fields.Many2one(
        comodel_name="event.event.ticket",
        readonly=True,
    )
    event_ticket_price = fields.Float(
        string="Ticket price",
        readonly=True,
    )
    event_registration_create_date = fields.Date(
        string="Registration Date",
        readonly=True,
    )
    event_registration_state = fields.Selection(
        selection=[
            ("draft", "Unconfirmed"),
            ("cancel", "Cancelled"),
            ("open", "Confirmed"),
            ("done", "Attended"),
        ],
        string="Registration Status",
        readonly=True,
    )
    active = fields.Boolean(string="Is registration active (not archived)?")
    event_registration_id = fields.Many2one(
        comodel_name="event.registration",
        readonly=True,
    )
    event_registration_name = fields.Char(
        string="Attendee Name",
        readonly=True,
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
    )
    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        readonly=True,
    )
    sale_order_date = fields.Datetime(
        string="Order Date",
        readonly=True,
    )
    sale_order_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        readonly=True,
    )
    sale_order_state = fields.Selection(
        selection=const.ORDER_STATE,
        string="Sale Order Status",
        readonly=True,
    )
    sale_order_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        readonly=True,
    )
    sale_order_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        readonly=True,
    )
    sale_price = fields.Float(
        string="Revenues",
        readonly=True,
    )
    sale_price_untaxed = fields.Float(
        string="Untaxed Revenues",
        readonly=True,
    )
    invoice_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Invoice Address",
        readonly=True,
    )
    sale_status = fields.Selection(
        selection=[
            ("to_pay", "Not Sold"),
            ("sold", "Sold"),
            ("free", "Free"),
        ],
        string="Payment Status",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            "CREATE OR REPLACE VIEW %s AS (%s);" % (self._table, self._query())
        )

    def _query(self, with_=None, select=None, join=None, group_by=None):
        return "\n".join(
            [
                self._with_clause(*(with_ or [])),
                self._select_clause(*(select or [])),
                self._from_clause(*(join or [])),
                self._group_by_clause(*(group_by or [])),
            ]
        )

    def _with_clause(self, *with_):
        # Extra clauses formatted as `cte1 AS (SELECT ...)`, `cte2 AS (SELECT ...)`...
        return (
            """
WITH
    """
            + ",\n    ".join(with_)
            if with_
            else ""
        )

    def _select_clause(self, *select):
        # Extra clauses formatted as `cte1.column1 AS new_column1`, `table1.column2 AS new_column2`...
        return """
SELECT
    -- One row per registration and no aggregation below, so the registration's
    -- own id is unique here and, unlike ROW_NUMBER(), stable: deleting a
    -- registration used to renumber every row after it, so a stored id then
    -- pointed at a different attendee.
    event_registration.id AS id,

    event_registration.id AS event_registration_id,
    event_event.company_id AS company_id,
    event_registration.event_id AS event_id,
    event_registration.event_slot_id AS event_slot_id,
    event_registration.event_ticket_id AS event_ticket_id,
    event_registration.create_date AS event_registration_create_date,
    event_registration.name AS event_registration_name,
    event_registration.state AS event_registration_state,
    event_registration.active AS active,
    event_registration.sale_order_id AS sale_order_id,
    event_registration.sale_order_line_id AS sale_order_line_id,
    event_registration.sale_status AS sale_status,

    event_event.event_type_id AS event_type_id,
    event_event.date_begin AS event_date_begin,
    event_event.date_end AS event_date_end,

    event_event_ticket.price AS event_ticket_price,

    sale_order.date_order AS sale_order_date,
    sale_order.partner_invoice_id AS invoice_partner_id,
    sale_order.partner_id AS sale_order_partner_id,
    sale_order.state AS sale_order_state,
    sale_order.user_id AS sale_order_user_id,

    sale_order_line.product_id AS product_id,
    CASE
        WHEN sale_order_line.product_uom_qty = 0 THEN 0
        ELSE
        sale_order_line.price_total
            / CASE COALESCE(sale_order.currency_rate, 0) WHEN 0 THEN 1.0 ELSE sale_order.currency_rate END
            / sale_order_line.product_uom_qty
    END AS sale_price,
    CASE
        WHEN sale_order_line.product_uom_qty = 0 THEN 0
        ELSE
        sale_order_line.price_subtotal
            / CASE COALESCE(sale_order.currency_rate, 0) WHEN 0 THEN 1.0 ELSE sale_order.currency_rate END
            / sale_order_line.product_uom_qty
    END AS sale_price_untaxed""" + (
            ",\n    " + ",\n    ".join(select) if select else ""
        )

    def _from_clause(self, *join_):
        # Extra clauses formatted as `column1`, `column2`...
        return """
FROM event_registration
LEFT JOIN event_event ON event_event.id = event_registration.event_id
LEFT JOIN event_event_ticket ON event_event_ticket.id = event_registration.event_ticket_id
LEFT JOIN sale_order ON sale_order.id = event_registration.sale_order_id
LEFT JOIN sale_order_line ON sale_order_line.id = event_registration.sale_order_line_id
""" + ("\n".join(join_) + "\n" if join_ else "")

    def _group_by_clause(self, *group_by):
        # Extra clauses formatted like `column1`, `column2`...
        return (
            """
GROUP BY
    """
            + ",\n    ".join(group_by)
            if group_by
            else ""
        )
