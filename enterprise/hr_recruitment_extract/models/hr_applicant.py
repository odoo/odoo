# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    def write(self, vals):
        res = super().write(vals)
        if not self or 'stage_id' not in vals:
            return res
        new_stage = self[0].stage_id
        if not new_stage.hired_stage:
            return res

        self.candidate_id._validate_ocr()
        return res
