# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
from odoo import fields, models


class EventSaleReport(models.Model):
    _inherit = 'event.sale.report'

    is_published = fields.Boolean('Is Published', readonly=True)

    def _query(self):
        return """
            %(with_clause)s
            %(select_clause)s
            FROM event_sale
            %(join_clause)s
            %(group_by_clause)s
        """ % {
            'with_clause': self._with_clause(),
            'select_clause': self._select_clause(),
            'join_clause': self._join_clause(),
            'group_by_clause': self._group_by_clause()
        }

    def _select_clause(self):
        return """
            SELECT
                ROW_NUMBER() OVER (ORDER BY event_sale.event_id) as id,
                event_sale.event_id as event_id,
                event_sale.event_ticket_ids as event_ticket_ids,
                SUM(event_sale.sale_price_total) as sale_price_total,
                SUM(event_sale.sale_price_subtotal) as sale_price_subtotal,
                event_event_ticket.seats_available as seats_available,
                event_event.is_published as is_published
        """

    def _join_clause(self):
        return """
            LEFT JOIN event_event_ticket ON event_sale.event_ticket_ids = event_event_ticket.id
            LEFT JOIN event_event ON event_event.id = event_sale.event_id
        """

    def _group_by_clause(self):
        return """
            GROUP BY
                event_sale.event_id,
                event_sale.event_ticket_ids,
                event_event_ticket.seats_available,
                event_event.is_published
        """

    def action_show_revenues(self):
        action = super().action_show_revenues()
        action['context'] = dict(ast.literal_eval(action.get('context', {})),
            search_default_is_published=1
        )
        return action
