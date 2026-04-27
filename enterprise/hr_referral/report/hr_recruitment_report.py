# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrRecruitmentReport(models.Model):
    _inherit = "hr.recruitment.report"

    has_referrer = fields.Integer(aggregator="sum", readonly=True)
    referral_hired = fields.Integer('# Hired by Referral', aggregator="sum", readonly=True)

    def _query(self, fields='', from_clause=''):
        fields += """
            , CASE WHEN a.ref_user_id IS NOT NULL THEN 1 ELSE 0 END as has_referrer,
            CASE WHEN a.date_closed IS NOT NULL AND a.ref_user_id IS NOT NULL THEN 1 ELSE 0 END as referral_hired
            """

        return super(HrRecruitmentReport, self)._query(fields, from_clause)
