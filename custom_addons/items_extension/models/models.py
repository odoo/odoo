# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class items_extension(models.Model):
#     _name = 'items_extension.items_extension'
#     _description = 'items_extension.items_extension'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

