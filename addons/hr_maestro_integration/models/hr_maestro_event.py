# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class HrMaestroEvent(models.Model):
    _name = 'hr.maestro.event'
    _description = 'Evento recebido da plataforma Maestro Intelligence (clima / NR-1)'
    _order = 'event_date desc, id desc'

    # Os payloads do Maestro são sempre agregados por empresa/equipe — a
    # plataforma não envia dados individuais identificáveis de funcionários
    # (ver disclaimer em build_event_payload do dispatcher do Maestro).
    company_id = fields.Many2one('res.company', string='Empresa (Odoo)', required=True,
                                  default=lambda self: self.env.company)
    maestro_company_id = fields.Char(string='ID da empresa no Maestro', required=True, index=True)
    event_type = fields.Selection([
        ('analysis.completed', 'Análise de clima concluída'),
        ('risk.identified', 'Risco psicossocial identificado'),
        ('risk.escalated', 'Risco escalado'),
        ('approval.pending', 'Aprovação pendente'),
        ('approval.decided', 'Aprovação decidida'),
        ('training.completed', 'Treinamento concluído'),
        ('pulse_survey.due', 'Pulse survey vencendo'),
        ('maturity.assessed', 'Maturidade avaliada'),
    ], string='Tipo de evento', required=True, index=True)
    event_date = fields.Datetime(string='Data do evento', required=True)
    external_event_id = fields.Char(string='ID do evento (idempotência)', required=True, index=True)
    department_id = fields.Many2one('hr.department', string='Departamento (se aplicável)')
    risk_level = fields.Selection([
        ('low', 'Baixo'),
        ('medium', 'Médio'),
        ('high', 'Alto'),
        ('critical', 'Crítico'),
    ], string='Nível de risco')
    summary = fields.Char(string='Resumo')
    data = fields.Text(string='Dados agregados (JSON)')

    _sql_constraints = [
        ('external_event_id_uniq', 'unique(external_event_id)',
         'Este evento do Maestro já foi registrado (idempotência).'),
    ]
