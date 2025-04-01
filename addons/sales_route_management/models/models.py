# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class sales_route_management(models.Model):
#     _name = 'sales_route_management.sales_route_management'
#     _description = 'sales_route_management.sales_route_management'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
