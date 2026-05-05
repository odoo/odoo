# from odoo import models, fields, api


# class ht_crm_ui(models.Model):
#     _name = 'ht_crm_ui.ht_crm_ui'
#     _description = 'ht_crm_ui.ht_crm_ui'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

