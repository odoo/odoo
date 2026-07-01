# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import fields, models

MAESTRO_LOGIN_MAX_ATTEMPTS = 5
MAESTRO_LOGIN_LOCKOUT_MINUTES = 15


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    maestro_external_id = fields.Char(
        string='ID externo (Maestro)', copy=False,
        help='Identificador do funcionário na plataforma Maestro Intelligence. '
             'Se vazio, o webhook tenta vincular pelo e-mail de trabalho.')
    maestro_event_ids = fields.One2many(
        'hr.maestro.event', 'employee_id', string='Eventos Maestro')
    maestro_event_count = fields.Integer(
        string='Eventos Maestro', compute='_compute_maestro_event_count')
    maestro_current_risk_level = fields.Selection([
        ('low', 'Baixo'),
        ('medium', 'Médio'),
        ('high', 'Alto'),
        ('critical', 'Crítico'),
    ], string='Risco psicossocial atual', compute='_compute_maestro_current_risk_level',
        help='Nível de risco do evento mais recente reportado pelo Maestro.')
    maestro_app_profile = fields.Selection(
        related='job_id.maestro_app_profile', string='Perfil no app Maestro',
        store=True, readonly=True,
        help='Definido pelo cargo (Cargo > Perfil no app Maestro). Controla '
             'a tela inicial que este funcionário acessa no app Maestro PWA.')
    maestro_login_fail_count = fields.Integer(
        string='Tentativas de login falhas (app Maestro)', default=0, copy=False)
    maestro_login_locked_until = fields.Datetime(
        string='Bloqueado até (app Maestro)', copy=False)

    def _maestro_app_login_locked(self):
        self.ensure_one()
        return bool(self.maestro_login_locked_until and self.maestro_login_locked_until > fields.Datetime.now())

    def _maestro_app_register_login_failure(self):
        self.ensure_one()
        fail_count = self.maestro_login_fail_count + 1
        values = {'maestro_login_fail_count': fail_count}
        if fail_count >= MAESTRO_LOGIN_MAX_ATTEMPTS:
            values['maestro_login_locked_until'] = fields.Datetime.now() + timedelta(
                minutes=MAESTRO_LOGIN_LOCKOUT_MINUTES)
        self.sudo().write(values)

    def _maestro_app_register_login_success(self):
        self.ensure_one()
        self.sudo().write({'maestro_login_fail_count': 0, 'maestro_login_locked_until': False})

    def _compute_maestro_event_count(self):
        counts = self.env['hr.maestro.event']._read_group(
            [('employee_id', 'in', self.ids)], ['employee_id'], ['__count'])
        mapped = {employee.id: count for employee, count in counts}
        for employee in self:
            employee.maestro_event_count = mapped.get(employee.id, 0)

    def _compute_maestro_current_risk_level(self):
        for employee in self:
            last_event = self.env['hr.maestro.event'].search(
                [('employee_id', '=', employee.id), ('risk_level', '!=', False)],
                order='event_date desc', limit=1)
            employee.maestro_current_risk_level = last_event.risk_level

    def action_view_maestro_events(self):
        self.ensure_one()
        return {
            'name': 'Eventos Maestro',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.maestro.event',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
