# coding: utf-8
from odoo import fields, models


class TypeCode(models.Model):
    _name = 'l10n_co_edi.type_code'
    _description = "Colombian EDI Type Code"

    name = fields.Char(required=True)
    description = fields.Char(required=True)
