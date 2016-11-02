# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Template(models.Model):
    _name = 'edi.template'

    name = fields.Char(string='Template name', required=True)
    xml_path = fields.Char(string='Template file', required=True)
    xsd_path = fields.Char(string='Schema file')
