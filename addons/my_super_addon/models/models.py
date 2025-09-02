# from odoo import models, fields, api


# class my_super_addon(models.Model):
#     _name = 'my_super_addon.my_super_addon'
#     _description = 'my_super_addon.my_super_addon'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

