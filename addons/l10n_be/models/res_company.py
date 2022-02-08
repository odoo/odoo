# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.

from odoo import api, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.depends('vat', 'country_id')
    def _compute_company_registry(self):
        # OVERRIDE
        # If a belgian company has a VAT number then it's company registry is it's VAT Number (without country code).
        super(ResCompany, self)._compute_company_registry()
        for company in self.filtered(lambda comp: comp.country_id.code == 'BE' and comp.vat):
            vat_country, vat_number = self.env['res.partner']._split_vat(company.vat)
            if vat_country == 'be' and self.env['res.partner'].simple_vat_check(vat_country, vat_number):
                company.company_registry = vat_number
