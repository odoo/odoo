# -*- coding: utf-8 -*-

from odoo import models, fields


class Validator(models.Model):
    _name = 'validator.validator'
    _description = 'validator.validator'

    name = fields.Char()
    contact = fields.Integer()