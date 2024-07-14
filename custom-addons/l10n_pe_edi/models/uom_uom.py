# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductUoM(models.Model):
    _inherit = 'uom.uom'

    l10n_pe_edi_measure_unit_code = fields.Char(
        'Measure unit code',
        help="Unit code that relates to a product in order to identify what measure unit it uses, the possible values"
        " that you can use here can be found in this URL")
