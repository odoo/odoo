# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    def write(self, vals):
        # Prevent the resource calendar of leaves to be updated by a write to
        # employee. When this module is enabled the resource calendar of
        # leaves are determined by those of the contracts.
        return super(HrEmployeeBase, self.with_context(no_leave_resource_calendar_update=True)).write(vals)
