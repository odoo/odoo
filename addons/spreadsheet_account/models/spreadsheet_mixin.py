# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models
from odoo.tools import date_utils


class SpreadsheetMixin(models.AbstractModel):
    _name = "spreadsheet.mixin"
    _inherit = "spreadsheet.mixin"

    def _get_spreadsheet_metadata(self, access_token=None):
        metadata = super()._get_spreadsheet_metadata(access_token=access_token)
        company = self.env.company
        start, end = date_utils.get_fiscal_year(
            fields.Date.context_today(self),
            day=company.fiscalyear_last_day,
            month=int(company.fiscalyear_last_month),
        )

        return {
            **metadata,
            "current_fiscal_year_start": fields.Date.to_string(start),
            "current_fiscal_year_end": fields.Date.to_string(end),
        }
