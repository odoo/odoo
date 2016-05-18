# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PropertyGroup(models.Model):
    """ Group of mrp properties."""
    _name = 'mrp.property.group'
    _description = 'Property Group'

    name = fields.Char('Property Group', required=True)
    description = fields.Text('Description')


class Property(models.Model):
    """ Properties of mrp """
    _name = 'mrp.property'
    _description = 'Property'

    name = fields.Char('Name', required=True)
    composition = fields.Selection([
        ('min', 'min'),
        ('max', 'max'),
        ('plus', 'plus')], string='Properties composition',
        default='min', required=True,
        help="Not used in computations, for information purpose only.")
    group_id = fields.Many2one('mrp.property.group', 'Property Group', required=True)
    description = fields.Text('Description')
