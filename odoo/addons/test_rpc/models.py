# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Test_RpcModel_A(models.Model):
    _description = "Model A"

    name = fields.Char(required=True)
    field_b1 = fields.Many2one("test_rpc.model_b", string="required field", required=True)
    field_b2 = fields.Many2one("test_rpc.model_b", string="restricted field", ondelete="restrict")


class Test_RpcModel_B(models.Model):
    _description = "Model B"

    name = fields.Char(required=True)
    value = fields.Integer()

    _qty_positive = models.Constraint(
        'check (value > 0)',
        "The value must be positive",
    )
