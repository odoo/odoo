# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class MailActivity(models.Model):
    _inherit = "mail.activity"

    note_id = fields.Many2one('project.task', string="Related To-Do", ondelete='cascade')
