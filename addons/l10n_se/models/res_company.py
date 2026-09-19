import re

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    org_number = fields.Char(compute="_compute_org_number")

    @api.depends("vat")
    def _compute_org_number(self):
        for company in self:
            if (
                company.account_config_id.account_fiscal_country_id.code == "SE"
                and company.vat
            ):
                org_number = re.sub(r"\D", "", company.vat)[:-2]
                org_number = org_number[:6] + "-" + org_number[6:]

                company.org_number = org_number
            else:
                company.org_number = ""
