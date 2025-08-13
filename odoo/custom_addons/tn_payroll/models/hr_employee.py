from odoo import models, fields, api

class Employee(models.Model):
    _inherit = 'hr.employee'

    cnss_number = fields.Char("CNSS Number")
    professional_category = fields.Selection([
        ('a', 'Catégorie A'),
        ('b', 'Catégorie B'),
        ('c', 'Catégorie C'),
    ], string="Catégorie Professionnelle")

    def generate_cnss_number(self):
        for rec in self:
            if not rec.cnss_number:
                rec.cnss_number = f'TN-{100000 + rec.id}'

