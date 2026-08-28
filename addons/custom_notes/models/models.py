# from odoo import models, fields, api


# class custom_notes(models.Model):
#     _name = 'custom_notes.custom_notes'
#     _description = 'custom_notes.custom_notes'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

