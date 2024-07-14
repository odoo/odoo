# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HelpdeskSLAReport(models.Model):
    _inherit = 'helpdesk.sla.report.analysis'

    remaining_hours_so = fields.Float('Remaining Hours on SO', readonly=True)
    sale_line_id = fields.Many2one('sale.order.line', string="Sales Order Item", readonly=True)

    def _select(self):
        return super()._select() + """ ,
            sol.remaining_hours as remaining_hours_so,
            T.sale_line_id as sale_line_id
        """

    def _group_by(self):
        return super()._group_by() + """ ,
            sol.remaining_hours,
            T.sale_line_id
        """

    def _from(self):
        from_str = super()._from()
        from_str += """
            LEFT JOIN sale_order_line sol ON T.sale_line_id = sol.id
        """
        return from_str
