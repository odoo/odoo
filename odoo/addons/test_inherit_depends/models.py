# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class PublicUnit(models.Model):
    _name = 'test.unit'
    _inherit = ['test.unit', 'test.inherit.mixin']
