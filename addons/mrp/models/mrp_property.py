# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class MrpPropertyGroup(models.Model):
    """
    Group of mrp properties.
    """
    _name = 'mrp.property.group'
    _description = 'Property Group'
    name = fields.Char(string='Property Group', required=True)
    description = fields.Text()


class MrpProperty(models.Model):
    """
    Properties of mrp.
    """
    _name = 'mrp.property'
    _description = 'Property'
    name = fields.Char(required=True)
    composition = fields.Selection([('min', 'min'), ('max', 'max'), ('plus', 'plus')], string='Properties composition', required=True, default='min', help="Not used in computations, for information purpose only.")
    group_id = fields.Many2one('mrp.property.group', string='Property Group', required=True)
    description = fields.Text()
