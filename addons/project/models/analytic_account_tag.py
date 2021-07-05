# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class AccountAnalyticTag(models.Model):
    _inherit = 'account.analytic.tag'

    task_ids = fields.Many2many('project.task', string='Tasks')
