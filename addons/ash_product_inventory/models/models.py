# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class ash_product_inventory(models.Model):
#     _name = 'ash_product_inventory.ash_product_inventory'
#     _description = 'ash_product_inventory.ash_product_inventory'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

