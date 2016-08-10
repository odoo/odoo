# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class Child0(models.Model):
    _name = 'delegation.child0'

    field_0 = fields.Integer()

class Child1(models.Model):
    _name = 'delegation.child1'

    field_1 = fields.Integer()

class Delegating(models.Model):
    _name = 'delegation.parent'

    _inherits = {
        'delegation.child0': 'child0_id',
        'delegation.child1': 'child1_id',
    }

    child0_id = fields.Many2one('delegation.child0', required=True, ondelete='cascade')
    child1_id = fields.Many2one('delegation.child1', required=True, ondelete='cascade')
