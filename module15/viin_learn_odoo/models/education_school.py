from odoo import fields, models

class EductionSchool(models.Model):
    _name = 'education.school'
    _description = 'School'
    
    name = fields.Char(string='Name', translate=True, required=True)
    code = fields.Char(string='Code', copy=False)
    address = fields.Char(string='Address')
    class_ids = fields.One2many('education.class', 'school_id', string='Classes')
    company_id = fields.Many2one('res.company',string='Company')
