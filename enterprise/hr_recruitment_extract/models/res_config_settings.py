# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    recruitment_extract_show_ocr_option_selection = fields.Selection(
        related='company_id.recruitment_extract_show_ocr_option_selection',
        string='Recruitment processing option',
        readonly=False)
