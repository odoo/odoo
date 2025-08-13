from odoo import models, fields

class Contract(models.Model):
    _inherit = 'hr.contract'

    cnss_employee_rate = fields.Float(string="Taux CNSS Employé (%)", default=9.18)
    cnss_employer_rate = fields.Float(string="Taux CNSS Employeur (%)", default=16.57)

    irpp_exempt = fields.Boolean(string="Exonéré IRPP", default=False)

    number_of_children = fields.Integer(string="Nombre d'enfants à charge", default=0)

    tunisian_contract_type = fields.Selection([
        ('cdi', 'CDI'),
        ('cdd', 'CDD'),
        ('stage', 'Stage'),
        ('autre', 'Autre'),
    ], string="Type de contrat (TN)", default='cdi')

    seniority_bonus_applicable = fields.Boolean(string="Prime d’ancienneté", default=True)
