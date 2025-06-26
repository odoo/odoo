# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# @author -  Fekete Mihai <feketemihai@gmail.com>
# Copyright (C) 2020 NextERP Romania (https://www.nexterp.ro) <contact@nexterp.ro>
# Copyright (C) 2015 Forest and Biomass Services Romania (http://www.forbiom.eu).
# Copyright (C) 2011 TOTAL PC SYSTEMS (http://www.erpsystems.ro).
# Copyright (C) 2009 (<http://www.filsystem.ro>)

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + ['nrc']

    nrc = fields.Char(string='NRC', help='Registration number at the Registry of Commerce')

    @api.depends('vat', 'country_id')
    def _compute_company_registry(self):
        # OVERRIDE
        # In Romania, if you have a VAT number, it's also your company registry (CUI) number
        super()._compute_company_registry()
        for partner in self.filtered(lambda p: p.country_id.code == 'RO' and p.vat):
            vat_country, vat_number = self._split_vat(partner.vat)
            if vat_country.isnumeric():
                vat_country = 'ro'
                vat_number = partner.vat
            if vat_country == 'ro' and self.simple_vat_check(vat_country, vat_number):
                partner.company_registry = vat_number
