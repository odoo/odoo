from odoo import models, fields,api

# class inheritance
class ClassInheritance(models.Model):
    _name = 'res.partner' # 可寫可不寫
    _inherit = ['res.partner']

    test_field2 = fields.Char('test_field')


    def ImportData(self):
        print(1)

    def report_missing_book(self):
        print(111)

