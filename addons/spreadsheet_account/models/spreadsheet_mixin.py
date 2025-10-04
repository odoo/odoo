# Part of Odoo. See LICENSE file for full copyright and licensing details.


from datetime import date

from odoo import models
from odoo.tools import date_utils


class SpreadsheetMixin(models.AbstractModel):
    _name = "spreadsheet.mixin"
    _inherit = ["spreadsheet.mixin"]

    def _get_spreadsheet_metadata(self, access_token=None):
        metadata = super()._get_spreadsheet_metadata(access_token=access_token)
        company = self.env["res.company"].browse(self.env.company.id)
        start, end = date_utils.get_fiscal_year(
            date.today(),
            day=company.fiscalyear_last_day,
            month=int(company.fiscalyear_last_month),
        )

        return {
            **metadata,
            "current_fiscal_year_start": start.isoformat(),
            "current_fiscal_year_end": end.isoformat(),
        }
