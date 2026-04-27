# coding: utf-8
from odoo import fields, models


class TaxType(models.Model):
    _name = 'l10n_co_edi.tax.type'
    _description = "Colombian EDI Tax Type"

    name = fields.Char(string=u'Name')
    description = fields.Char(string=u'Descripción')
    code = fields.Char(string=u'Código', required=True)
    retention = fields.Boolean(string=u'Retencion')
