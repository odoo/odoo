# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    documents_hr_settings = fields.Boolean(
        related='company_id.documents_hr_settings', readonly=False, string="Human Resources")
    documents_hr_folder = fields.Many2one(
        'documents.folder', related='company_id.documents_hr_folder', readonly=False, string="hr default workspace")

    @api.onchange('documents_hr_folder')
    def _onchange_documents_hr_folder(self):
        # Implemented in other documents-hr bridge modules
        pass
