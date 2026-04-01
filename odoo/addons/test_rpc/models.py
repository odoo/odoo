# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Test_RpcModel_A(models.Model):
    _name = 'test_rpc.model_a'
    _description = "Model A"

    name = fields.Char(required=True)
    field_b1 = fields.Many2one("test_rpc.model_b", string="required field", required=True)
    field_b2 = fields.Many2one("test_rpc.model_b", string="restricted field", ondelete="restrict")

    @api.private
    def private_method(self):
        return "private"

    def filtered(self, func):
        return super().filtered(func)

    @api.model
    def not_depending_on_id(self, vals=None):
        return f"got {vals}"


class Test_RpcModel_B(models.Model):
    _name = 'test_rpc.model_b'
    _description = "Model B"

    name = fields.Char(required=True)
    value = fields.Integer()

    _qty_positive = models.Constraint(
        'check (value > 0)',
        "The value must be positive",
    )
