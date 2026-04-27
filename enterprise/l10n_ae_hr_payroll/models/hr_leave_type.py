# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    l10n_ae_is_annual_leave = fields.Boolean(
        string="Is Annual Leave", compute="_compute_l10n_ae_is_annual_leave", store=True, readonly=False,
        help="If checked, this time off type will be counted in annual leaves computation.")

    @api.depends("requires_allocation")
    def _compute_l10n_ae_is_annual_leave(self):
        self.l10n_ae_is_annual_leave = False
