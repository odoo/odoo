# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_peppol_endpoint_value(self, country_code, field):
        # Keep this entry point for stable compatibility after moving the logic to account_edi_ubl_cii.
        # TODO: Remove this compatibility override in master.
        return super()._get_peppol_endpoint_value(country_code, field)  # noqa: OLS03028
