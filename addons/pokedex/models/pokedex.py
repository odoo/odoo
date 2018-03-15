# -*- coding: utf-8 -*-
from odoo import fields, models


class Type(models.Model):
    _name = 'pokedex.type'
    _description = 'Type of Pokemon'

    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer('Color Index')

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Pokémon Type cannot be duplicated'),
    ]


class Pokemon(models.Model):
    _name = 'pokedex.pokemon'
    _description = 'Pokemon'
    _order = 'sequence, id'

    sequence = fields.Integer('#', required=True)
    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer('Color Index')
    image = fields.Binary('Image')
    height = fields.Integer()
    weight = fields.Integer()
    captured = fields.Selection([('0', 'Not Captured'), ('1', 'Captured')], 'Captured', select=True)
    types_ids = fields.Many2many(comodel_name='pokedex.type', string='Types')
    parent_id = fields.Many2one('pokedex.pokemon', 'Parent', select=True)
    children_ids = fields.One2many('pokedex.pokemon', 'parent_id', 'Evolutions')
