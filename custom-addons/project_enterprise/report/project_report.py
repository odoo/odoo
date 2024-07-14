# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import api, fields, models


class ReportProjectTaskUser(models.Model):
    _inherit = 'report.project.task.user'

    planned_date_begin = fields.Datetime("Start date", readonly=True)

    def _select(self):
        return super()._select() + """,
            t.planned_date_begin
        """

    def _group_by(self):
        return super()._group_by() + """,
            t.planned_date_begin
        """
