from odoo import fields, models

class EducationStudentCopy(models.Model):
    _name = 'education.student.copy'
    _inherit = 'education.student'
    _description = 'Education Student - Copy'