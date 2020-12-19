# -*- coding: utf-8 -*-

from odoo import models, fields, api


class sale_inheritance(models.Model):
    _inherit = 'res.partner'
    test_field = fields.Char('test_field')
