# -*- coding: utf-8 -*-

from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    unece_code_tax = fields.Many2one('unece.code',
        string='UNECE Tax Type',
        domain=[('type_id.name', '=', 'UN/ECE 5153')],
        required=True,
        default=lambda self: self.env.ref('base_unece.code_type_tax_vat'),
        help="Select the Tax Type Code of the official "
        "nomenclature of the United Nations Economic "
        "Commission for Europe (UNECE), DataElement 5153")