# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Template(models.Model):
    _name = 'edi.template'

    path = fields.Char(string='Template path', required=True)
    name = fields.Char(string='Template name', required=True)
