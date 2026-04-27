from odoo import models

class HrContract(models.Model):
    _inherit = 'hr.contract'

    def _get_resource_calendar_leaves(self, start_dt, end_dt):
        # prevent leaves that are associated with a blocked payslip to be taken
        # into account, as they will be deferred lated.
        return super()._get_resource_calendar_leaves(start_dt, end_dt).filtered(lambda l: l.holiday_id.payslip_state != 'blocked')
