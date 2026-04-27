# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class HRLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    l10n_ch_swissdec_payroll_impact = fields.Boolean("Impacts Swiss Payroll", default=False)
    l10n_ch_swissdec_work_interruption = fields.Boolean("Work Interruption", default=False)