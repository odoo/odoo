# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    document_spreadsheet_folder_id = fields.Many2one(
        'documents.document', related='company_id.document_spreadsheet_folder_id', readonly=False)
