# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrContractEmployeeReport(models.Model):
    _inherit = "hr.contract.employee.report"

    final_yearly_costs = fields.Float('Annual Employee Budget', aggregator="avg", readonly=True)

    def _query(self, fields='', from_clause='', outer=''):
        fields += """
            , c.final_yearly_costs AS final_yearly_costs"""

        return super(HrContractEmployeeReport, self)._query(fields, from_clause, outer)
