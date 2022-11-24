# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2022 Daj Mi 5 . All rights reserved.

from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('vat', 'country_id')
    def _compute_company_registry(self):
        # OVERRIDE
        # If a croatian company has a VAT number then it's company registry (OIB)
        # is it's VAT Number (without country code).
        # borrowed from l10n_be
        super()._compute_company_registry()
        for partner in self.filtered(lambda p: p.country_id.code == 'HR' and p.vat):
            vat_country, vat_number = self._split_vat(partner.vat)
            if vat_country == 'HR' and self.simple_vat_check(vat_country, vat_number):
                partner.company_registry = vat_number
