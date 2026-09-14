from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_worklocation(self, start_date, end_date):
        employees = self.env["hr.employee"].search(
            [
                ("partner_id", "in", self.ids),
                ("company_id", "in", self.env.companies.ids),
            ]
        )
        return employees._get_worklocation(start_date, end_date)
