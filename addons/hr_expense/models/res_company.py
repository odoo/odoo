# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    expense_extract_show_ocr_option_selection = fields.Selection([
        ('no_send', 'Do not digitalize bills'),
        ('manual_send', "Digitalize bills on demand only"),
        ('auto_send', 'Digitalize all bills automatically')], string="Send mode on expense attachments",
        required=False, default='auto_send')
