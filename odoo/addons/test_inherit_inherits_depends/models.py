# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class TestInheritBird(models.Model):
    _name = 'test.inherit.bird'
    _inherit = ['test.inherit.animal']
    _description = 'Test Inherit Bird'

    name = fields.Char(default='Bird')


class TestInheritOwl(models.Model):
    _name = 'test.inherit.owl'
    _inherit = ['test.inherit.bird']
    _description = 'Test Inherit Owl'


class TestInheritPet(models.Model):
    _name = 'test.inherit.pet'
    _inherits = {'test.inherit.animal': 'animal_id'}
    _description = 'Test Inherit Pet'

    name = fields.Char(default='Pet')
    animal_id = fields.Many2one('test.inherit.animal', required=True, ondelete='restrict')
