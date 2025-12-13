# from odoo import models, fields, api


# class via_suite_base(models.Model):
#     _name = 'via_suite_base.via_suite_base'
#     _description = 'via_suite_base.via_suite_base'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

