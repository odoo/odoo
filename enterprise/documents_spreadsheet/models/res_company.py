# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _default_document_spreadsheet_folder_id(self):
        folder = self.env.ref('documents_spreadsheet.document_spreadsheet_folder', raise_if_not_found=False)
        if not folder or folder.company_id:
            return False
        return folder

    document_spreadsheet_folder_id = fields.Many2one(
        'documents.document', check_company=True,
        default=_default_document_spreadsheet_folder_id,
        domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)],
    )

    @api.constrains('document_spreadsheet_folder_id')
    def _check_documents_spreadsheet_folder_id(self):
        for company in self:
            folder = company.document_spreadsheet_folder_id
            if folder.company_id and folder.company_id != company:
                raise ValidationError(_("The company of %(folder)s should either be undefined or set to %(company)s. "
                                        "Otherwise, it is not possible to link the workspace to the company.",
                                        folder=folder.display_name, company=company.display_name))
