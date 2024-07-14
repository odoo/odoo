# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import fields, models

from odoo.addons.sale.models.sale_order import INVOICE_STATUS


class ReportProjectTaskUser(models.Model):
    _name = 'report.project.task.user.fsm'
    _inherit = 'report.project.task.user.fsm'

    invoice_status = fields.Selection(INVOICE_STATUS, string='Invoice Status', readonly=True)

    def _select(self):
        return super()._select() + """,
            so.invoice_status as invoice_status
        """

    def _group_by(self):
        return super()._group_by() + """,
            so.invoice_status
        """

    def _from(self):
        return super()._from() + """
            LEFT JOIN sale_order so ON t.sale_order_id = so.id
        """
