# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

UOM_TO_UNECE_CODE = {
    'uom.product_uom_unit': 'C62',
    'uom.product_uom_dozen': 'DZN',
    'uom.product_uom_kgm': 'KGM',
    'uom.product_uom_gram': 'GRM',
    'uom.product_uom_day': 'DAY',
    'uom.product_uom_hour': 'HUR',
    'uom.product_uom_minute': 'MIN',
    'uom.product_uom_ton': 'TNE',
    'uom.product_uom_meter': 'MTR',
    'uom.product_uom_km': 'KMT',
    'uom.product_uom_cm': 'CMT',
    'uom.product_uom_litre': 'LTR',
    'uom.product_uom_lb': 'LBR',
    'uom.product_uom_oz': 'ONZ',
    'uom.product_uom_inch': 'INH',
    'uom.product_uom_foot': 'FOT',
    'uom.product_uom_mile': 'SMI',
    'uom.product_uom_floz': 'OZA',
    'uom.product_uom_qt': 'QT',
    'uom.product_uom_gal': 'GLL',
    'uom.product_uom_cubic_meter': 'MTQ',
    'uom.product_uom_cubic_inch': 'INQ',
    'uom.product_uom_cubic_foot': 'FTQ',
    'uom.uom_square_meter': 'MTK',
    'uom.uom_square_foot': 'FTK',
    'uom.product_uom_yard': 'YRD',
    'uom.product_uom_millimeter': 'MMT',
    'uom.product_uom_kwh': 'KWH',
}


class UomUom(models.Model):
    _inherit = "uom.uom"

    fiscal_country_codes = fields.Char(compute="_compute_fiscal_country_codes")

    @api.depends_context("allowed_company_ids")
    def _compute_fiscal_country_codes(self):
        for record in self:
            record.fiscal_country_codes = ",".join(self.env.companies.mapped("account_fiscal_country_id.code"))

    def _get_unece_code(self):
        """ Returns the UNECE code used for international trading for corresponding to the UoM as per
        https://unece.org/fileadmin/DAM/cefact/recommendations/rec20/rec20_rev3_Annex2e.pdf"""
        xml_ids = self._get_external_ids().get(self.id, [])
        matches = list(set(xml_ids) & set(UOM_TO_UNECE_CODE.keys()))
        return matches and UOM_TO_UNECE_CODE[matches[0]] or 'C62'

    @api.model
    def _get_uom_from_unece_code(self, unece_code):
        unece_code_to_uom = {v: k for k, v in UOM_TO_UNECE_CODE.items()}
        uom_xmlid = unece_code_to_uom.get(unece_code, 'uom.product_uom_unit')
        return self.env.ref(uom_xmlid, raise_if_not_found=False)
