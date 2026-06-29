# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class HrMaestroEvent(models.Model):
    _name = 'hr.maestro.event'
    _description = 'Evento individual recebido da plataforma Maestro Intelligence (clima / NR-1)'
    _inherit = ['mail.thread']
    _order = 'event_date desc, id desc'
    _rec_name = 'summary'

    employee_id = fields.Many2one('hr.employee', string='Funcionário', required=True,
                                   index=True, ondelete='cascade', tracking=True)
    department_id = fields.Many2one(related='employee_id.department_id', string='Departamento', store=True)
    company_id = fields.Many2one('res.company', string='Empresa (Odoo)', required=True,
                                  default=lambda self: self.env.company)
    maestro_company_id = fields.Char(string='ID da empresa no Maestro', required=True, index=True)
    event_type = fields.Selection([
        ('risk.identified', 'Risco identificado'),
        ('risk.escalated', 'Risco escalado'),
        ('approval.pending', 'Aprovação pendente'),
        ('approval.decided', 'Aprovação decidida'),
        ('training.completed', 'Treinamento concluído'),
        ('pulse_survey.due', 'Pulse survey vencendo'),
        ('maturity.assessed', 'Maturidade avaliada'),
    ], string='Tipo de evento', required=True, index=True, tracking=True)
    event_date = fields.Datetime(string='Data do evento', required=True)
    external_event_id = fields.Char(string='ID do evento (idempotência)', required=True, index=True)
    risk_level = fields.Selection([
        ('low', 'Baixo'),
        ('medium', 'Médio'),
        ('high', 'Alto'),
        ('critical', 'Crítico'),
    ], string='Nível de risco', tracking=True)
    risk_score = fields.Float(string='Índice de risco')
    summary = fields.Char(string='Resumo')
    data = fields.Text(string='Dados originais (JSON)')

    _sql_constraints = [
        ('external_event_id_uniq', 'unique(external_event_id)',
         'Este evento do Maestro já foi registrado (idempotência).'),
    ]
