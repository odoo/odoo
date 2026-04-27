# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    expense_extract_show_ocr_option_selection = fields.Selection([
        ('no_send', 'Do not digitize'),
        ('manual_send', "Digitize on demand only"),
        ('auto_send', 'Digitize automatically')], string="Send mode on expense attachments",
        required=False, default='auto_send')
