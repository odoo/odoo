# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

PUSH_NOTIFIED_EVENT_TYPES = {'risk.identified', 'risk.escalated', 'approval.pending'}
PUSH_NOTIFIED_RISK_LEVELS = {'high', 'critical'}


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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if (record.event_type in PUSH_NOTIFIED_EVENT_TYPES
                    or record.risk_level in PUSH_NOTIFIED_RISK_LEVELS):
                self.env['hr.maestro.push.device']._notify_employee(
                    record.employee_id,
                    title='Maestro Intelligence',
                    body=record.summary or dict(
                        record._fields['event_type'].selection).get(record.event_type, ''),
                    url='/maestro/app',
                )
            if record.event_type == 'training.completed':
                record._sync_training_skill()
        return records

    def _sync_training_skill(self):
        self.ensure_one()
        try:
            payload = json.loads(self.data or '{}')
        except ValueError:
            return
        skill_name = payload.get('skill_name')
        if not skill_name:
            return
        skill = self.env['hr.skill'].search([('name', '=', skill_name)], limit=1)
        if not skill:
            _logger.info('Maestro: skill "%s" não encontrada em hr.skill, ignorando sincronização.', skill_name)
            return
        level_name = payload.get('skill_level_name')
        skill_levels = skill.skill_type_id.skill_level_ids
        level = skill_levels.filtered(lambda l: l.name == level_name) if level_name else self.env['hr.skill.level']
        if not level:
            level = skill_levels.filtered('default_level') or skill_levels[:1]
        self.env['hr.employee.skill'].create({
            'employee_id': self.employee_id.id,
            'skill_type_id': skill.skill_type_id.id,
            'skill_id': skill.id,
            'skill_level_id': level.id,
        })
