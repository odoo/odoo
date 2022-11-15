# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class viin_learn_odoo(models.Model):
#     _name = 'viin_learn_odoo.viin_learn_odoo'
#     _description = 'viin_learn_odoo.viin_learn_odoo'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
