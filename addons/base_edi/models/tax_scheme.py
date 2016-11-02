# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools

class TaxScheme(models.Model):
    _name = 'edi.fact'
    
    name = fields.Char(string='UN/EDIFACT name', required=True, 
        help='United Nations/Electronic Data Interchange for Administration, Commerce and Transport (UN/EDIFACT).')
    scheme_id = fields.Char(string='Scheme ID', required=True, help='Identifices the ID type')
    scheme_name = fields.Char(string='Scheme Name', required=True, help='Name of the scheme')
    scheme_agency_id = fields.Integer(string='Scheme agency ID', required=True, help='Specifies the ID of the ID issuer')