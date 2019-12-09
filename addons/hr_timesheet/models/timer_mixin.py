# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class TimerMixin(models.AbstractModel):
    _name = 'timer.mixin'
    _description = 'Timer Mixin'

    timer_start = fields.Datetime("Timer Start")
    timer_pause = fields.Datetime("Timer Last Pause")

    # is_timer_running field is used with timer_toggle_button widget
    # to create a timer button in the view.
    # If the timer field is set on False,
    # then it displays a button with fa-icon-play icon.
    # Otherwise, it displays a button with fa-icon-stop icon
    is_timer_running = fields.Boolean(compute="_compute_timer")

    @api.depends('timer_start')
    def _compute_timer(self) -> None:
        for record in self:
            record.is_timer_running = bool(record.timer_start)

    def action_timer_start(self) -> None:
        """ Action start the timer.

            Start timer and search if another timer hasn't been launched.
            If yes, then stop the timer before launch this timer.
        """
        self.ensure_one()
        if not self.timer_start:
            self.write({'timer_start': fields.Datetime.now()})

    def action_timer_stop(self):
        """ Stop the timer and return the spent minutes since it started
            :return minutes_spent if the timer is started,
                    otherwise return False
        """
        self.ensure_one()
        if not self.timer_start:
            return False
        minutes_spent = self._get_minutes_spent()
        self.write({'timer_start': False, 'timer_pause': False})
        return minutes_spent

    def _get_minutes_spent(self) -> float:
        """ Compute the minutes spent with the timer

            :return minutes spent
        """
        start_time = self.timer_start
        stop_time = fields.Datetime.now()

        # timer was either running or paused
        if self.timer_pause:
            start_time += (stop_time - self.timer_pause)

        return (stop_time - start_time).total_seconds() / 60

    def action_timer_pause(self) -> None:
        self.write({'timer_pause': fields.Datetime.now()})

    def action_timer_resume(self) -> None:
        new_start = self.timer_start + (fields.Datetime.now() - self.timer_pause)
        self.write({'timer_start': new_start, 'timer_pause': False})

    def get_server_time(self):
        """ Get the time of the server

            The problem with the timer, it's the time can be different between server side and client side.
            We need to have the time of the server and don't use the local time. Then, we have a timer beginning at 0:00
            and not 23:59 or something else.
        """
        return fields.Datetime.now()
