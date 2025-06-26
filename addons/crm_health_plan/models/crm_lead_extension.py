from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    health_plan_type = fields.Selection([
        ('individual', 'Individual'),
        ('family', 'Familiar'),
        ('corporate', 'Corporativo'),
    ], string='Tipo de Plano de Saúde')

    health_plan_ids = fields.Many2many('crm.health.plan', string='Planos de Interesse')
