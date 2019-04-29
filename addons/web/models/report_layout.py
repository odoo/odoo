# -*- coding: ascii -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class View(models.Model):

    _name = "report.layout"
    _description = 'Report Layout'

    view_id = fields.Many2one('ir.ui.view', 'Document Template', required=True)
    image = fields.Char(string="Preview image src")
    pdf = fields.Char(string="Preview pdf src")

    name = fields.Char()
    primary_color = fields.Char(string="Default primary color")
    secondary_color = fields.Char(string="Default secondary color")
