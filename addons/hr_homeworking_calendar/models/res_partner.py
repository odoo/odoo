from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_worklocation(self, start_date, end_date):
        employees = self.env["hr.employee"].search(
            [
                ("partner_id", "in", self.ids),
                ("company_id", "in", self.env.companies.ids),
            ]
        )
        _debug.logic("worklocation_by_partner", partners=self, employees=employees)
        return employees._get_worklocation(start_date, end_date)
