from odoo import fields, models
from odoo.osv import expression


class ResCompany(models.Model):
    _inherit = 'res.company'

    documents_account_peppol_folder_id = fields.Many2one(
        comodel_name='documents.document',
        string="Document Workspace",
        check_company=True,
        domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)]
    )
    documents_account_peppol_tag_ids = fields.Many2many(
        comodel_name='documents.tag',
        string="Document Tags",
    )

    def _compute_peppol_purchase_journal_id(self):
        # OVERRIDE account_peppol
        for company in self:
            if not company.documents_account_peppol_folder_id:
                # Only force a journal when a folder is not set.
                super(ResCompany, company)._compute_peppol_purchase_journal_id()

    def _get_used_folder_ids_domain(self, folder_ids):
        return expression.OR([
            super()._get_used_folder_ids_domain(folder_ids),
            [
                ('documents_account_peppol_folder_id', 'in', folder_ids),
                ('account_peppol_proxy_state', '=', 'not_registered')
            ],
        ])
