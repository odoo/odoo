# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

import barcode
from odoo import models, fields, api, _
from datetime import datetime
import random


class GenerateProductBarcode(models.TransientModel):
    _name = 'generate.product.barcode'
    _description = 'Generate Product Barcode'

    overwrite_ean13 = fields.Boolean(string="Overwrite Barcode")
    barcode_selection = fields.Selection([('code_39', 'CODE 39'), ('code_128', 'CODE 128'),
                                          ('ean_13', 'EAN-13'), ('ean_8', 'EAN-8'),
                                          ('isbn_13', 'ISBN 13'), ('isbn_10', 'ISBN 10'),
                                          ('issn', 'ISSN'), ('upca', 'UPC-A')], string="Barcode Selection")
    overwrite_internal_ref = fields.Boolean(string="Overwrite Internal Reference")

    @api.model
    def default_get(self, fieldsname):
        res = super(GenerateProductBarcode, self).default_get(fieldsname)
        param_obj = self.env['ir.config_parameter'].sudo()
        if param_obj.get_param('gen_barcode'):
            res.update({'barcode_selection': param_obj.get_param('barcode_selection')})
        return res

    def generate_barcode(self):
        for rec in self.env['product.product'].browse(self._context.get('active_ids')):
            if not self.overwrite_ean13 and rec.barcode:
                continue
            if self.barcode_selection == 'code_39':
                barcode_code = barcode.codex.Code39(str(rec.id) + datetime.now().strftime("%S%M%H%d%m%y"))
            if self.barcode_selection == 'code_128':
                barcode_code = barcode.codex.Code39(str(rec.id) + datetime.now().strftime("%S%M%H%d%m%y"))
            if self.barcode_selection == 'ean_13':
                barcode_code = barcode.ean.EuropeanArticleNumber13(
                    str(rec.id) + datetime.now().strftime("%S%M%H%d%m%y"))
            if self.barcode_selection == 'ean_8':
                barcode_code = barcode.ean.EuropeanArticleNumber8(str(rec.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if len(barcode_code.get_fullcode()) > 8:
                    barcode_code = barcode_code.get_fullcode()[:8]
            if self.barcode_selection == 'isbn_13':
                barcode_code = barcode.isxn.InternationalStandardBookNumber13(
                    '978' + str(rec.id) + datetime.now().strftime("%S%M%H%d%m%y"))
            if self.barcode_selection == 'isbn_10':
                barcode_code = barcode.isxn.InternationalStandardBookNumber10(
                    str(rec.id) + datetime.now().strftime("%S%M%H%d%m%y"))
            if self.barcode_selection == 'issn':
                barcode_code = barcode.isxn.InternationalStandardSerialNumber(
                    str(rec.id) + datetime.now().strftime("%S%M%H%d%m%y"))
                if len(str(barcode_code)) > 8:
                    barcode_code = str(barcode_code)[:8]
            if self.barcode_selection == 'upca':
                barcode_code = barcode.upc.UniversalProductCodeA(str(rec.id) + datetime.now().strftime("%S%M%H%d%m%y"))

            if self.barcode_selection in ['ean_8', 'issn']:
                rec.write({'barcode': barcode_code})
            else:
                rec.write({'barcode': barcode_code.get_fullcode()})
        return True

    def generate_internal_reference(self):
        for rec in self.env['product.product'].browse(self._context.get('active_ids')):
            if not self.overwrite_internal_ref and rec.default_code:
                continue
            rec.write({'default_code': (str(rec.id).zfill(6) + str(random.randint(10, 99)))[:8]})
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
