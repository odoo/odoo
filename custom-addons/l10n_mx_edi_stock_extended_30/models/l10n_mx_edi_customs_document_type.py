# -*- coding: utf-8 -*-

from odoo import fields, models


class MexicanEDICustomsDocumentType(models.Model):
    _name = 'l10n_mx_edi.customs.document.type'
    _description = 'Mexican Customs Document Type'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    goods_direction = fields.Selection(
        selection=[
            ('import', 'Import'),
            ('export', 'Export'),
            ('both', 'Import, Export'),
        ],
        string='Type',
        required=True,
    )

    _sql_constraints = [
        ('uniq_code', 'UNIQUE(code)', 'This code is already used.'),
    ]
