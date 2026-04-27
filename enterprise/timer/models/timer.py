# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class TimerTimer(models.Model):
    _name = 'timer.timer'
    _description = 'Timer Module'

    timer_start = fields.Datetime("Timer Start", export_string_translation=False)
    timer_pause = fields.Datetime("Timer Last Pause", export_string_translation=False)
    is_timer_running = fields.Boolean(compute="_compute_is_timer_running", export_string_translation=False)
    res_model = fields.Char(required=True, export_string_translation=False)
    res_id = fields.Integer(required=True, export_string_translation=False)
    user_id = fields.Many2one('res.users', export_string_translation=False)

    _sql_constraints = [(
        'unique_timer', 'UNIQUE(res_model, res_id, user_id)',
        'Only one timer occurrence by model, record and user')]

    @api.depends('timer_start', 'timer_pause')
    def _compute_is_timer_running(self):
        for record in self:
            record.is_timer_running = record.timer_start and not record.timer_pause

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Reset the user_timer_id to force the recomputation
            self.env[vals['res_model']].browse(vals['res_id']).invalidate_model(['user_timer_id'])
        return super().create(vals_list)

    def action_timer_start(self):
        if not self.timer_start:
            self.write({'timer_start': fields.Datetime.now()})

    def action_timer_stop(self):
        """ Stop the timer and return the spent minutes since it started
            :return minutes_spent if the timer is started,
                    otherwise return False
        """
        if not self.timer_start:
            return False
        minutes_spent = self._get_minutes_spent()
        self.write({'timer_start': False, 'timer_pause': False})
        return minutes_spent

    def _get_minutes_spent(self):
        start_time = self.timer_start
        stop_time = fields.Datetime.now()
        # timer was either running or paused
        if self.timer_pause:
            start_time += (stop_time - self.timer_pause)
        return (stop_time - start_time).total_seconds() / 60

    def action_timer_pause(self):
        self.write({'timer_pause': fields.Datetime.now()})

    def action_timer_resume(self):
        if self.timer_start and self.timer_pause:
            new_start = self.timer_start + (fields.Datetime.now() - self.timer_pause)
            self.write({'timer_start': new_start, 'timer_pause': False})

    @api.model
    @api.readonly
    def get_server_time(self):
        """ Returns the server time.
            The timer widget needs the server time instead of the client time
            to avoid time desynchronization issues like the timer beginning at 0:00
            and not 23:59 and so on.
        """
        return fields.Datetime.now()
