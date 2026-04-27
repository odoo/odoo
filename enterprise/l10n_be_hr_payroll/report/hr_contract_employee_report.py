# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrContractEmployeeReport(models.Model):
    _inherit = "hr.contract.employee.report"

    fuel_card = fields.Float('Fuel Card', aggregator="avg", readonly=True)
    fte = fields.Float('Full Time Equivalent (Today)', readonly=True)

    def _query(self, fields='', from_clause='', outer=''):
        fields += """
            , c.fuel_card AS fuel_card
            , cal.hours_per_week AS hours_per_week
            , cal_company.hours_per_week AS hours_per_week_company"""

        from_clause += """
            left join resource_calendar cal on cal.id = c.resource_calendar_id
            left join res_company company on company.id = e.company_id
            left join resource_calendar cal_company on cal_company.id = company.resource_calendar_id
        """

        outer += """
            , CASE WHEN date_part('month', NOW()) = date_part('month', date) AND date_part('year', Now()) = date_part('year', date) THEN age_sum * hours_per_week / hours_per_week_company ELSE NULL END as fte
        """

        return super(HrContractEmployeeReport, self)._query(fields, from_clause, outer)
