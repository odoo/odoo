from odoo import models, fields

class HealthPlan(models.Model):
    _name = 'crm.health.plan'
    _description = 'Plano de Saúde'

    name = fields.Char(string="Nome do Plano", required=True)
    operator = fields.Many2one('res.partner', string="Operadora")
    coverage = fields.Selection([
        ('regional', 'Regional'),
        ('nacional', 'Nacional'),
    ], string='Abrangência')
    price = fields.Float(string='Preço Base')
