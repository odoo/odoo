from odoo import models, fields

# https://www.odoo.com/forum/help-1/question/whats-the-difference-between-inherit-and-inherits-52205


# class inheritance
class ClassInheritance(models.Model):
    _name = 'hr.expense' # 可寫可不寫
    _inherit = ['hr.expense']

    test_field = fields.Char('test_field')

