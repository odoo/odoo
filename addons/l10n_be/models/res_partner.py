# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.

from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('vat', 'country_id')
    def _compute_company_registry(self):
        # OVERRIDE
        # If a belgian company has a VAT number then its company registry is its VAT Number (without country code).
        super()._compute_company_registry()
        for partner in self.filtered(lambda p: p.country_id.code == 'BE' and p.vat):
            vat_country, vat_number = self._split_vat(partner.vat)
            if vat_country.isnumeric():
                vat_country = 'be'
                vat_number = partner.vat
            if vat_country == 'be' and self.simple_vat_check(vat_country, vat_number):
                partner.company_registry = vat_number
