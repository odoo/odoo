# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    event_id = fields.Many2one("event.event", "Event", readonly=True)
    event_ticket_id = fields.Many2one("event.event.ticket", "Event Ticket", readonly=True)

    def _query(self, with_clause="", fields=None, groupby="", from_clause=""):
        fields = fields or {}
        fields["event_id"] = ", l.event_id as event_id"
        fields["event_ticket_id"] = ", l.event_ticket_id as event_ticket_id"
        groupby += ", l.event_id, l.event_ticket_id"
        return super()._query(with_clause, fields, groupby, from_clause)
