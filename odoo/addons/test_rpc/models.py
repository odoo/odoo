# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ModelA(models.Model):
    _name = "test_rpc.model_a"
    _description = "Model A"

    name = fields.Char(required=True)
    field_b1 = fields.Many2one("test_rpc.model_b", string="required field", required=True)
    field_b2 = fields.Many2one("test_rpc.model_b", string="restricted field", ondelete="restrict")


class ModelB(models.Model):
    _name = "test_rpc.model_b"
    _description = "Model B"

    name = fields.Char(required=True)
    value = fields.Integer()

    _sql_constraints = [
        ('qty_positive', 'check (value > 0)', 'The value must be positive'),
    ]
