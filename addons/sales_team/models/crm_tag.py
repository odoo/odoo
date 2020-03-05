# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Tag(models.Model):

    _name = "crm.tag"
    _description = "CRM Tag"

    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer('Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
