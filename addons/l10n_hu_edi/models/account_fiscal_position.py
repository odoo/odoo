# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    @api.model
    def _get_fiscal_position(self, partner, delivery=None):
        """
        :return: fiscal position found (recordset)
        :rtype: :class:`account.fiscal.position`
        """
        if not partner:
            return super()._get_fiscal_position(partner, delivery=delivery)

        company = self.env.company
        intra_eu = vat_exclusion = False
        if company.vat and partner.vat:
            eu_country_codes = set(self.env.ref("base.europe").country_ids.mapped("code"))
            # custom modification starts here
            # Hungarian VAT number can have this format: "12345678-1-12"
            intra_eu = (company.vat[:2] in eu_country_codes or company.country_id.code == "HU") and (
                partner.vat[:2] in eu_country_codes or partner.country_id.code == "HU"
            )
            vat_exclusion = company.vat[:2] == partner.vat[:2] or (
                company.country_id.code == "HU" and partner.country_id.code == "HU"
            )
            # custom modification ends here

        # If company and partner have the same vat prefix (and are both within the EU), use invoicing
        if not delivery or (intra_eu and vat_exclusion):
            delivery = partner

        # partner manually set fiscal position always win
        manual_fiscal_position = delivery.property_account_position_id or partner.property_account_position_id
        if manual_fiscal_position:
            return manual_fiscal_position

        # First search only matching VAT positions
        vat_required = bool(partner.vat)
        fp = self._get_fpos_by_region(delivery.country_id.id, delivery.state_id.id, delivery.zip, vat_required)

        # Then if VAT required found no match, try positions that do not require it
        if not fp and vat_required:
            fp = self._get_fpos_by_region(delivery.country_id.id, delivery.state_id.id, delivery.zip, False)

        return fp or self.env["account.fiscal.position"]
