from odoo import models,fields

class Teacher(models.Model):
    _name = "wb.teacher"
    _description = "This is teacher Profile"

    name = fields.Char('Name')
    yos = fields.Integer('Years of Service')
    subject = fields.Char('Subject')
    age = fields.Integer('Age')
    salary = fields.Float('Salary')
    address = fields.Text('Address')
    isActive = fields.Boolean('Is Active', default=True)