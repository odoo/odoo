# coding: utf-8
from odoo import fields, models


class ProductUom(models.Model):
    _inherit = 'uom.uom'

    l10n_co_edi_ubl = fields.Char(string=u'Colombia Código UBL')
