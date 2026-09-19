from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import date_utils

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.readonly
    @api.model
    def get_fiscal_dates(self, payload):
        companies = self.env["res.company"].browse(
            data["company_id"] or self.env.company.id for data in payload
        )
        existing_companies = companies.exists()
        # prefetch both fields
        existing_companies.account_config_id.fetch(
            ["fiscalyear_last_day", "fiscalyear_last_month"]
        )
        results = []

        for data, company in zip(payload, companies, strict=True):
            if company not in existing_companies:
                results.append(False)
                continue
            start, end = date_utils.get_fiscal_year(
                fields.Date.to_date(data["date"]),
                day=company.account_config_id.fiscalyear_last_day,
                month=int(company.account_config_id.fiscalyear_last_month),
            )
            results.append({"start": start, "end": end})
        _debug.pipeline(
            "spreadsheet_fiscal_dates_computed",
            requests=len(payload),
            unknown_companies=sum(1 for result in results if result is False),
        )
        return results
