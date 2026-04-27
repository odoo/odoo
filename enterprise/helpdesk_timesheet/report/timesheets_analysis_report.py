# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TimesheetsAnalysisReport(models.Model):
    _inherit = "timesheets.analysis.report"

    helpdesk_ticket_id = fields.Many2one("helpdesk.ticket", "Helpdesk Ticket", readonly=True)

    @api.model
    def _select(self):
        return super()._select() + """,
                A.helpdesk_ticket_id AS helpdesk_ticket_id
        """
