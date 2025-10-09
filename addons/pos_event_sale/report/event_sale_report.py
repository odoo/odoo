# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventSaleReport(models.Model):
    _inherit = "event.sale.report"

    def _query(self, with_=None, select=None, join=None, group_by=None, where=None):
        where_clause = """event_registration.pos_order_line_id IS NULL"""
        res = super()._query(with_, select, join, group_by, (where or []) + [where_clause])
        return (
            res
            + f"""UNION ALL (
            SELECT {self._select_pos(*(select or []))}
            FROM {self._from_pos()}
            WHERE {self._where_pos()}
            )
        """
        )

    def _where_pos(self):
        return """pos_order_line.event_ticket_id is not NULL"""

    def _select_pos(self):
        # Extra clauses formatted as `cte1.column1 AS new_column1`, `table1.column2 AS new_column2`...
        select_query = """
ROW_NUMBER() OVER (ORDER BY event_registration.id) AS id,
event_registration.id AS event_registration_id,
event_registration.company_id AS company_id,
event_registration.event_id AS event_id,
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
pos_order.date_order AS sale_order_date,
pos_order.partner_id AS invoice_partner_id,
pos_order.partner_id AS sale_order_partner_id,
pos_order.state AS sale_order_state,
pos_order.user_id AS sale_order_user_id,
pos_order_line.product_id AS product_id,
CASE
    WHEN pos_order_line.qty = 0 THEN 0
    ELSE
    pos_order_line.price_subtotal_incl / pos_order_line.qty
END AS sale_price,
CASE
    WHEN pos_order_line.qty = 0 THEN 0
    ELSE
    pos_order_line.price_subtotal / pos_order_line.qty
END AS sale_price_untaxed"""
        additional_fields = self._select_additional_fields()
        if additional_fields:
            select_query += ",\n    " + ",\n    ".join(f"{v} AS {k}" for k, v in additional_fields.items())
        return select_query

    def _from_pos(self, *join_):
        # Extra clauses formatted as `column1`, `column2`...
        return """
event_registration event_registration
LEFT JOIN pos_order_line ON pos_order_line.id= event_registration.pos_order_line_id
LEFT JOIN pos_order ON pos_order.id = pos_order_line.order_id
LEFT JOIN event_event ON event_event.id = event_registration.event_id
LEFT JOIN event_event_ticket ON event_event_ticket.id = event_registration.event_ticket_id
""" + ("\n".join(join_) + "\n" if join_ else "")
