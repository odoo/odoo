# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions

class UNECECode(models.Model):
    _name = 'unece.code'

    unece_type = fields.Char(string='Type', required=True)
    unece_code = fields.Char(string='Code', required=True)
    unece_name = fields.Char(string='Name', required=True)
    unece_description = fields.Char(string='Description')

    _sql_constraints = [(
        'type_code_uniq',
        'unique(unece_code, unece_name)',
        'An UNECE code of the same type already exists'
        )]
