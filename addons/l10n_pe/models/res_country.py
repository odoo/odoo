# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCountry(models.Model):
    _inherit = "res.country"

    def _get_address_format_fields_mapping(self):
        return {
            **super()._get_address_format_fields_mapping(),
            "l10n_pe_district_name": "l10n_pe_district",
        }
