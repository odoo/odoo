# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models,fields

class CustomAccountMove(models.Model):
    _inherit = 'account.move.line'
    cost = fields.Float(compute="_onchange_move", store=True)

    @api.onchange('product_id')
    def _onchange_move(self):
        for record in self:
            record.cost = record.product_id.standard_price
# class custom(models.Model):
#     _name = 'custom.custom'
#     _description = 'custom.custom'<field name="quantity"/>

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
