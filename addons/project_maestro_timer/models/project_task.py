# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    timer_ids = fields.One2many(
        'project.task.timer', 'task_id', string='Cronômetros')

    # Campo computado: estado do timer do usuário logado (para a view)
    user_timer_status = fields.Char(
        string='Estado do cronômetro (usuário atual)',
        compute='_compute_user_timer_status', store=False)
    user_timer_accumulated = fields.Float(
        string='Horas acumuladas (sessão atual)',
        compute='_compute_user_timer_status', store=False)

    @api.depends('timer_ids.timer_start', 'timer_ids.timer_accumulated', 'timer_ids.user_id')
    def _compute_user_timer_status(self):
        uid = self.env.uid
        for task in self:
            timer = task.timer_ids.filtered(lambda t: t.user_id.id == uid)[:1]
            if not timer:
                task.user_timer_status = 'idle'
                task.user_timer_accumulated = 0.0
            elif timer.timer_start:
                task.user_timer_status = 'running'
                task.user_timer_accumulated = timer.timer_accumulated
            elif timer.timer_accumulated:
                task.user_timer_status = 'paused'
                task.user_timer_accumulated = timer.timer_accumulated
            else:
                task.user_timer_status = 'idle'
                task.user_timer_accumulated = 0.0

    # ── Métodos chamados pelo widget via ORM RPC ───────────────────────────────

    def action_timer_start(self):
        self.ensure_one()
        timer = self.env['project.task.timer'].get_or_create(self.id)
        timer.action_start()

    def action_timer_pause(self):
        self.ensure_one()
        timer = self.env['project.task.timer'].search(
            [('task_id', '=', self.id), ('user_id', '=', self.env.uid)], limit=1)
        if timer:
            timer.action_pause()

    def action_timer_stop(self, description=''):
        self.ensure_one()
        timer = self.env['project.task.timer'].search(
            [('task_id', '=', self.id), ('user_id', '=', self.env.uid)], limit=1)
        if timer:
            timer.action_save(description=description)
        return True

    def action_timer_discard(self):
        self.ensure_one()
        timer = self.env['project.task.timer'].search(
            [('task_id', '=', self.id), ('user_id', '=', self.env.uid)], limit=1)
        if timer:
            timer.action_discard()

    def action_timer_state(self):
        self.ensure_one()
        return self.env['project.task.timer'].timer_state(self.id)
