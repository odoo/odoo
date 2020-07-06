# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrRecruitmentSourceReport(models.Model):
    _inherit = "hr.recruitment.source.report"

    click = fields.Integer(string="# Click", group_operator="sum", readonly=True)
    cost_by_click = fields.Integer('Cost by Click', group_operator="avg", readonly=True)

    def _query(self, fields='', from_clause='', left_join_clause='', groupby_fields=''):
        fields += """
            , lt.count as click
            , (cost/ NULLIF(lt.count, 0)) as cost_by_click
            """
        left_join_clause += """ LEFT JOIN link_tracker lt ON lt.id = s.link_tracker_id """

        groupby_fields += """, lt.count """


        return super(HrRecruitmentSourceReport, self)._query(fields, from_clause, left_join_clause, groupby_fields)
