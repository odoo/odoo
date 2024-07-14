# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    documents_hr_contracts_tags = fields.Many2many(
        'documents.tag', 'documents_hr_contracts_tags_table', related='company_id.documents_hr_contracts_tags',
        readonly=False, string="Contracts")

    @api.onchange('documents_hr_folder')
    def _onchange_documents_hr_folder(self):
        super()._onchange_documents_hr_folder()
        if self.documents_hr_folder != self.documents_hr_contracts_tags.folder_id:
            self.documents_hr_contracts_tags = False
