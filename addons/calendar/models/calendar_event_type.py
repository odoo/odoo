# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MeetingType(models.Model):

    _name = 'calendar.event.type'
    _description = 'Event Meeting Type'

    name = fields.Char('Name', required=True)
    color = fields.Integer('Color', default=5)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
