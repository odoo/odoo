# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions

class UneceAgency(models.Model):
    _name = 'unece.agency'

    code = fields.Integer(string='Code', index=True)
    name = fields.Char(string='Name', index=True)
    description = fields.Char(string='Description')


class UneceType(models.Model):
    _name = 'unece.type'

    agency_id = fields.Many2one('unece.agency', required=True)
    name = fields.Char(string='Name', index=True)


class UneceCode(models.Model):
    _name = 'unece.code'


    type_id = fields.Many2one('unece.type', required=True)
    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    description = fields.Char(string='Description')

    _sql_constraints = [(
        'type_code_uniq',
        'unique(code, name)',
        'An UN/ECE code of the same type already exists'
        )]
