from odoo import models, api, fields

from odoo.tools import date_utils


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def get_fiscal_dates(self, payload):
        companies = self.env["res.company"].browse(
            data["company_id"] or self.env.company.id for data in payload
        )
        existing_companies = companies.exists()
        # prefetch both fields
        existing_companies.fetch(["fiscalyear_last_day", "fiscalyear_last_month"])
        results = []

        for data, company in zip(payload, companies):
            if company not in existing_companies:
                results.append(False)
                continue
            start, end = date_utils.get_fiscal_year(
                fields.Date.to_date(data["date"]),
                day=company.fiscalyear_last_day,
                month=int(company.fiscalyear_last_month),
            )
            results.append({"start": start, "end": end})
        return results
