# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import fields, models


class ReportProjectTaskUser(models.Model):
    _inherit = 'report.project.task.user'

    worksheet_template_id = fields.Many2one('worksheet.template', string="Worksheet Template", readonly=True)

    def _select(self):
        return super()._select() + """,
            t.worksheet_template_id
        """

    def _group_by(self):
        return super()._group_by() + """,
                t.worksheet_template_id
        """
