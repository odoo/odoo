# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    _order = "priority desc, id desc"

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Very High')], string="Priority", help="Gives the sequence order when displaying a list of tasks.")
