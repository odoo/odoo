# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from math import ceil

class TimerMixin(models.AbstractModel):
    _name = 'timer.mixin'
    _description = 'Timer Mixin'

    timer_start = fields.Datetime(related='user_timer_id.timer_start')
    timer_pause = fields.Datetime(related='user_timer_id.timer_pause')
    is_timer_running = fields.Boolean(related='user_timer_id.is_timer_running', search="_search_is_timer_running")
    user_timer_id = fields.One2many('timer.timer', compute='_compute_user_timer_id', search='_search_user_timer_id')

    display_timer_start_primary = fields.Boolean(compute='_compute_display_timer_buttons')
    display_timer_stop = fields.Boolean(compute='_compute_display_timer_buttons')
    display_timer_pause = fields.Boolean(compute='_compute_display_timer_buttons')
    display_timer_resume = fields.Boolean(compute='_compute_display_timer_buttons')

    def _search_is_timer_running(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported'))

        running_timer_query = self.env['timer.timer']._search([
            ('timer_start', '!=', False),
            ('timer_pause', '=', False),
            ('res_model', '=', self._name),
        ])

        if operator == '!=':
            value = not value

        return [('id', 'inselect' if value else 'not inselect', running_timer_query.select('res_id'))]

    def _search_user_timer_id(self, operator, value):
        timer_query = self.env['timer.timer']._search([
            ('id', operator, value),
            ('user_id', '=', self.env.user.id),
            ('res_model', '=', self._name),
        ])
        return [('id', 'inselect', timer_query.select('res_id'))]

    @api.depends_context('uid')
    def _compute_user_timer_id(self):
        """ Get the timers according these conditions
            :user_id is is the current user
            :res_id is the current record
            :res_model is the current model
            limit=1 by security but the search should never have more than one record
        """
        timer_read_group = self.env['timer.timer']._read_group(
            domain=[
                ('user_id', '=', self.env.user.id),
                ('res_id', 'in', self.ids),
                ('res_model', '=', self._name),
            ],
            groupby=['res_id'],
            aggregates=['id:array_agg'])
        timer_by_model = dict(timer_read_group)
        for record in self:
            record.user_timer_id = timer_by_model.get(record.id, False)

    @api.model
    def _get_user_timers(self):
        # Return user's timers. Can have multiple timers if some are in pause
        return self.env['timer.timer'].search([('user_id', '=', self.env.user.id)])

    def action_timer_start(self):
        """ Start the timer of the current record
        First, if a timer is running, stop or pause it
        If there isn't a timer for the current record, create one then start it
        Otherwise, resume or start it
        """
        self.ensure_one()
        self._stop_timer_in_progress()
        timer = self.user_timer_id
        if not timer:
            timer = self.env['timer.timer'].create({
                'timer_start': False,
                'timer_pause': False,
                'is_timer_running': False,
                'res_model': self._name,
                'res_id': self.id,
                'user_id': self.env.user.id,
            })
            timer.action_timer_start()
        else:
            # Check if it is in pause then resume it or start it
            if timer.timer_pause:
                timer.action_timer_resume()
            else:
                timer.action_timer_start()

    def action_timer_stop(self):
        """ Stop the timer of the current record
        Unlink the timer, it's useless to keep the stopped timer.
        A new timer can be create if needed
        Return the amount of minutes spent
        """
        self.ensure_one()
        timer = self.user_timer_id
        minutes_spent = timer.action_timer_stop()
        timer.unlink()
        return minutes_spent

    def action_timer_pause(self):
        self.ensure_one()
        timer = self.user_timer_id
        timer.action_timer_pause()

    def action_timer_resume(self):
        self.ensure_one()
        self._stop_timer_in_progress()
        timer = self.user_timer_id
        timer.action_timer_resume()

    def _action_interrupt_user_timers(self):
        # Interruption is the action called when the timer is stoped by the start of another one
        self.action_timer_pause()

    def _stop_timer_in_progress(self):
        """
        Cancel the timer in progress if there is one
        Each model can interrupt the running timer in a specific way
        By setting it in pause or stop by example
        """
        timer = self._get_user_timers().filtered(lambda t: t.is_timer_running)
        if timer:
            model = self.env[timer.res_model].browse(timer.res_id)
            model._action_interrupt_user_timers()

    @api.depends('timer_start', 'timer_pause')
    def _compute_display_timer_buttons(self):
        for record in self:
            start_p, stop, pause, resume = True, True, True, True
            if record.timer_start:
                start_p = False
                if record.timer_pause:
                    pause = False
                else:
                    resume = False
            record.update({
                'display_timer_start_primary': start_p,
                'display_timer_stop': stop,
                'display_timer_pause': pause,
                'display_timer_resume': resume,
            })

    @api.model
    def _timer_rounding(self, minutes_spent, minimum, rounding):
        minutes_spent = max(minimum, minutes_spent)
        if rounding and ceil(minutes_spent % rounding) != 0:
            minutes_spent = ceil(minutes_spent / rounding) * rounding
        return minutes_spent
