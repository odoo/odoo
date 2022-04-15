# -*- coding: utf-8 -*-

from odoo import models


class UoM(models.Model):
    _inherit = 'uom.uom'

    def _get_unece_code(self):
        """ Returns the UNECE code used for international trading for corresponding to the UoM as per
        https://unece.org/fileadmin/DAM/cefact/recommendations/bkup_htm/add2d.htm.
        """
        if len(self) != 1:
            return 'C62'

        xml_id = self.env['ir.model.data'].search([
                ('model', '=', 'uom.uom'),
                ('res_id', '=', self.id),
        ]).name
        mapping = {
            'product_uom_unit': 'C62',
            'product_uom_dozen': 'DZN',
            'product_uom_kgm': 'KGM',
            'product_uom_gram': 'GRM',
            'product_uom_day': 'DAY',
            'product_uom_hour': 'HUR',
            'product_uom_ton': 'TNE',
            'product_uom_meter': 'MTR',
            'product_uom_km': 'KTM',
            'product_uom_cm': 'CMT',
            'product_uom_litre': 'LTR',
            'product_uom_lb': 'LBR',
            'product_uom_oz': 'ONZ',
            'product_uom_inch': 'INH',
            'product_uom_foot': 'FOT',
            'product_uom_mile': 'SMI',
            'product_uom_floz': 'OZA',
            'product_uom_qt': 'QT',
            'product_uom_gal': 'GLL',
            'product_uom_cubic_meter': 'MTQ',
            'product_uom_cubic_inch': 'INQ',
            'product_uom_cubic_foot': 'FTQ',
        }
        return mapping.get(xml_id, 'C62')
