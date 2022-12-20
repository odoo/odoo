# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class RecurrentMixin(models.AbstractModel):
    _name = 'recurrent.mixin'
    _description = 'Recurrent Mixin'
    _recurrence_model = "recurrence.mixin"

    # =====================================================
    #  * Fields *
    # =====================================================
    repeat = fields.Boolean(string="Recurrent")
    recurrence_id = fields.Many2one(_recurrence_model, copy=False)

    repeat_interval = fields.Integer(string='Repeat Every', default=1, compute='_compute_repeat', readonly=False)
    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='week', compute='_compute_repeat', readonly=False)
    repeat_type = fields.Selection([
        ('forever', 'Forever'),
        ('until', 'Until'),
        ('number', 'Number of Repetitions'),
    ], string="Until", default="forever", compute='_compute_repeat', readonly=False)
    repeat_until = fields.Date(string="End Date", compute='_compute_repeat', readonly=False)
    repeat_number = fields.Integer(string="Repetitions", default=1, compute='_compute_repeat', readonly=False)

    recurrence_update = fields.Selection([
        ('this', 'This task'),
        ('subsequent', 'This and future tasks'),
    ], default='this', store=False)
    recurrence_message = fields.Char(string='Next Occurences', compute='_compute_recurrence_message')

    # =====================================================
    #  * Static methods *
    # =====================================================
    @api.model
    def _get_recurrence_fields(self):
        return [
            'repeat_interval',
            'repeat_unit',
            'repeat_type',
            'repeat_until',
            'repeat_number',
        ]

    # =====================================================
    #  * Computes *
    # =====================================================
    @api.depends('repeat')
    def _compute_repeat(self):
        rec_fields = self._get_recurrence_fields()
        defaults = self.default_get(rec_fields)
        for task in self:
            for f in rec_fields:
                if task.recurrence_id:
                    task[f] = task.recurrence_id[f]
                else:
                    if task.repeat:
                        task[f] = defaults.get(f)
                    else:
                        task[f] = False

    @api.depends(
        'repeat',
        'repeat_interval',
        'repeat_unit',
        'repeat_type',
        'repeat_until',
        'repeat_number'
    )
    def _compute_recurrence_message(self):
        return
