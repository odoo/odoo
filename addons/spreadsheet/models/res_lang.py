# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from odoo.addons.spreadsheet.utils.formatting import (
    strftime_format_to_spreadsheet_date_format,
    strftime_format_to_spreadsheet_time_format,
)


class ResLang(models.Model):
    _inherit = "res.lang"

    @api.readonly
    @api.model
    def get_locales_for_spreadsheet(self):
        """Return the list of locales available for a spreadsheet."""
        langs = self.with_context(active_test=False).search([])

        spreadsheet_locales = [lang._odoo_lang_to_spreadsheet_locale() for lang in langs]
        return spreadsheet_locales

    @api.model
    def _get_user_spreadsheet_locale(self):
        """Convert the odoo lang to a spreadsheet locale."""
        lang = self._lang_get(self.env.user.lang or 'en_US')
        return lang._odoo_lang_to_spreadsheet_locale()

    def _odoo_lang_to_spreadsheet_locale(self):
        """Convert an odoo lang to a spreadsheet locale."""
        return {
            "name": self.name,
            "code": self.code,
            "thousandsSeparator": self.thousands_sep,
            "decimalSeparator": self.decimal_point,
            "dateFormat": strftime_format_to_spreadsheet_date_format(self.date_format),
            "timeFormat": strftime_format_to_spreadsheet_time_format(self.time_format),
            "formulaArgSeparator": ";" if self.decimal_point == "," else ",",
            "weekStart": int(self.week_start),
        }
