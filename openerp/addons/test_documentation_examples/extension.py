# -*- coding: utf-8 -*-

from openerp import models, fields

class Extension0(models.Model):
    _name = 'extension.0'

    name = fields.Char(default="A")

class Extension1(models.Model):
    _inherit = 'extension.0'

    description = fields.Char(default="Extended")
