# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions

class UnedifactAgency(models.Model):
    _name = 'unedifact.agency'

    code = fields.Integer(string='Code', index=True)
    name = fields.Char(string='Name', index=True)
    description = fields.Char(string='Description')


class UnedifactType(models.Model):
    _name = 'unedifact.type'

    agency_id = fields.Many2one('unedifact.agency', required=True)
    name = fields.Char(string='Name', index=True)


class UnedifactCode(models.Model):
    _name = 'unedifact.code'


    type_id = fields.Many2one('unedifact.type', required=True)
    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    description = fields.Char(string='Description')

    _sql_constraints = [(
        'type_code_uniq',
        'unique(code, name)',
        'An UN/EDIFACT code of the same type already exists'
        )]
