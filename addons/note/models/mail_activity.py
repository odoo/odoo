# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    category = fields.Selection(selection_add=[('reminder', 'Reminder')])


class MailActivity(models.Model):
    _inherit = "mail.activity"

    note_id = fields.Many2one('note.note', string="Related Note", ondelete='cascade')
