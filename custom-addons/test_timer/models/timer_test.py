# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class TimerTest(models.Model):
    """ A very simple model only inheriting from timer.mixin to test
    timer features """
    _description = 'Timer Model'
    _name = 'timer.test'
    _inherit = ['timer.mixin']

    name = fields.Char(required=True)


class OverrideInterruptionTimerTest(models.Model):
    """ A very simple model inheriting from timer.mixin and
    overriding _action_interrupt_user_timers() """
    _description = 'Interruption Timer Model'
    _name = 'interruption.timer.test'
    _inherit = ['timer.mixin']

    def _action_interrupt_user_timers(self):
        self.action_timer_stop()
