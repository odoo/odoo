# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class ResState(models.Model):
    _name = 'res.country.state'
    _inherit = 'res.country.state'

    parent_id = fields.Many2one(
        'res.country.state', 'Parent State', index=True,
        domain="[('type', '=', 'view'), ('id', '!=', id)]")
    child_ids = fields.One2many(
        'res.country.state', 'parent_id', string='Child States')
    type = fields.Selection(
        [('view', 'View'), ('normal', 'Normal')], 'Type', default='normal')
