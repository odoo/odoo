# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ForumPostReason(models.Model):
    _description = "Post Closing Reason"
    _order = 'name'

    name = fields.Char(string='Closing Reason', required=True, translate=True)
    reason_type = fields.Selection([('basic', 'Basic'), ('offensive', 'Offensive')], string='Reason Type', default='basic')
