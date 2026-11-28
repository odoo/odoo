# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    @api.onchange('employee_id', 'accrual_plan_id')
    def _onchange_l10n_mx_date_from(self):
        for allocation in self:
            if (
                not allocation._origin
                and allocation.accrual_plan_id
                and allocation.employee_id.company_id.country_code == 'MX'
            ):
                allocation.date_from = allocation.employee_id._get_first_version_date() or allocation.date_from
