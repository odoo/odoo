# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""
project.task.timer — rastreamento de tempo por usuário × tarefa, estilo Bitrix24.

Estados por registro (user_id + task_id):
  running  → timer_start IS NOT NULL  (cronômetro ativo)
  paused   → timer_start IS NULL AND timer_accumulated > 0
  idle     → sem registro (nunca iniciado) ou timer_accumulated = 0 após reset

Regra "uma tarefa por vez": ao iniciar em B, o timer ativo do mesmo usuário
em qualquer outra tarefa é automaticamente pausado.
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

MIN_SECONDS = 5  # sessões menores que isso são ignoradas ao pausar/salvar


class ProjectTaskTimer(models.Model):
    _name = 'project.task.timer'
    _description = 'Cronômetro de Tarefa por Usuário'

    task_id = fields.Many2one(
        'project.task', string='Tarefa', required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one(
        'res.users', string='Usuário', required=True, ondelete='cascade', index=True,
        default=lambda self: self.env.uid)
    employee_id = fields.Many2one(
        'hr.employee', string='Funcionário', compute='_compute_employee', store=True)
    timer_start = fields.Datetime(string='Início da sessão atual', readonly=True, copy=False)
    timer_accumulated = fields.Float(
        string='Horas acumuladas (sessões pausadas)', default=0.0, copy=False,
        help='Total de horas das sessões pausadas anteriores (não inclui a sessão em curso).')

    _sql_constraints = [
        ('user_task_uniq', 'unique(task_id, user_id)', 'Já existe um timer para este usuário nesta tarefa.'),
    ]

    @api.depends('user_id')
    def _compute_employee(self):
        for rec in self:
            rec.employee_id = self.env['hr.employee'].search(
                [('user_id', '=', rec.user_id.id), ('active', '=', True)], limit=1)

    # ── estado ────────────────────────────────────────────────────────────────

    @property
    def is_running(self):
        return bool(self.timer_start)

    def _elapsed_hours_current_session(self):
        if not self.timer_start:
            return 0.0
        return (fields.Datetime.now() - self.timer_start).total_seconds() / 3600.0

    def _total_hours(self):
        return self.timer_accumulated + self._elapsed_hours_current_session()

    # ── ações ─────────────────────────────────────────────────────────────────

    def action_start(self):
        """Inicia ou retoma o cronômetro. Pausa automaticamente qualquer outro timer ativo do mesmo usuário."""
        self.ensure_one()
        if self.timer_start:
            return  # já em execução

        # Pausa todos os outros timers ativos deste usuário
        others = self.search([
            ('user_id', '=', self.user_id.id),
            ('timer_start', '!=', False),
            ('id', '!=', self.id),
        ])
        for other in others:
            other._do_pause()

        self.write({'timer_start': fields.Datetime.now()})

    def action_pause(self):
        """Pausa o cronômetro, acumulando o tempo da sessão atual."""
        self.ensure_one()
        self._do_pause()

    def _do_pause(self):
        if not self.timer_start:
            return
        elapsed = self._elapsed_hours_current_session()
        if elapsed * 3600 >= MIN_SECONDS:
            self.write({
                'timer_accumulated': self.timer_accumulated + elapsed,
                'timer_start': False,
            })
        else:
            self.write({'timer_start': False})

    def action_save(self, description=''):
        """Para o cronômetro, cria a linha de timesheet e reseta o timer."""
        self.ensure_one()
        total = self._total_hours()
        if total * 3600 >= MIN_SECONDS and self.employee_id and self.task_id.project_id:
            self.env['account.analytic.line'].sudo().create({
                'project_id': self.task_id.project_id.id,
                'task_id': self.task_id.id,
                'employee_id': self.employee_id.id,
                'name': description.strip() if description else f'Cronômetro · {self.task_id.name}',
                'unit_amount': total,
                'date': fields.Date.today(),
            })
        self.write({'timer_start': False, 'timer_accumulated': 0.0})

    def action_discard(self):
        """Descarta o tempo sem salvar."""
        self.ensure_one()
        self.write({'timer_start': False, 'timer_accumulated': 0.0})

    # ── API para o controller/widget ──────────────────────────────────────────

    @api.model
    def get_or_create(self, task_id):
        timer = self.search([('task_id', '=', task_id), ('user_id', '=', self.env.uid)], limit=1)
        if not timer:
            timer = self.create({'task_id': task_id})
        return timer

    @api.model
    def timer_state(self, task_id):
        """Retorna o estado do timer do usuário atual para a tarefa."""
        timer = self.search([('task_id', '=', task_id), ('user_id', '=', self.env.uid)], limit=1)
        if not timer:
            return {'status': 'idle', 'accumulated_seconds': 0, 'timer_start': False}
        return {
            'status': 'running' if timer.timer_start else ('paused' if timer.timer_accumulated else 'idle'),
            'accumulated_seconds': round(timer.timer_accumulated * 3600),
            'timer_start': timer.timer_start and fields.Datetime.to_string(timer.timer_start),
        }
