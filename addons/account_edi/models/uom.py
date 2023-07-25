# -*- coding: utf-8 -*-

from odoo import models


class UoM(models.Model):
    _inherit = 'uom.uom'

    def _get_unece_code(self):
        """ Returns the UNECE code used for international trading for corresponding to the UoM as per
        https://unece.org/fileadmin/DAM/cefact/recommendations/rec20/rec20_rev3_Annex2e.pdf"""
        mapping = {
            'uom.product_uom_unit': 'C62',
            'uom.product_uom_dozen': 'DZN',
            'uom.product_uom_kgm': 'KGM',
            'uom.product_uom_gram': 'GRM',
            'uom.product_uom_day': 'DAY',
            'uom.product_uom_hour': 'HUR',
            'uom.product_uom_ton': 'TNE',
            'uom.product_uom_meter': 'MTR',
            'uom.product_uom_km': 'KTM',
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
        }
        xml_ids = self._get_external_ids().get(self.id, [])
        matches = list(set(xml_ids) & set(mapping.keys()))
        return matches and mapping[matches[0]] or 'C62'
