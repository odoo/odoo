from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    documents_account_peppol_folder_id = fields.Many2one(
        related='company_id.documents_account_peppol_folder_id',
        readonly=False
    )
    documents_account_peppol_tag_ids = fields.Many2many(
        related='company_id.documents_account_peppol_tag_ids',
        readonly=False
    )
