# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class ReportExportWizard(models.TransientModel):
    """ Extends the report export wizard to give it the ability to save the
    attachments it generates as documents, in a folder of the Documents app.
    """
    _inherit = 'account_reports.export.wizard'

    def _get_default_folder(self):
        return (
            self.env.company.account_folder_id
            if self.env.company.documents_account_settings
            else self.env.ref('documents.document_finance_folder', raise_if_not_found=False)
        )

    folder_id = fields.Many2one(string="Folder", comodel_name='documents.document',
        help="Folder where to save the generated file", required=True,
        default=_get_default_folder, domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)])
    tag_ids = fields.Many2many('documents.tag', 'export_wiz_document_tag_rel', string="Tags")

    @api.onchange('folder_id')
    def on_folder_id_change(self):
        self.tag_ids = False

    def export_report(self):
        # When making the export with Documents app installed, we want the resulting action to open the folder of Documents where
        # the attachments were saved, with only them visible, instead of the regular ir.attachment objects.
        self.ensure_one()
        created_attachments = self.env['documents.document']
        for vals in self._get_attachments_to_save():
            created_attachments |= self.env['documents.document'].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Documents'),
            'view_mode': 'kanban',
            'res_model': 'documents.document',
            'domain': [],
            'context': {
                'searchpanel_default_folder_id': self.folder_id.id,
                'searchpanel_default_tag_ids': self.tag_ids.ids,
            },
            'view_id': self.env.ref('documents.document_view_kanban').id,
        }


class ReportExportWizardOption(models.TransientModel):
    _inherit = 'account_reports.export.wizard.format'

    def get_attachment_vals(self, file_name, file_content, mimetype, log_options_dict):
        rslt = super().get_attachment_vals(file_name, file_content, mimetype, log_options_dict)
        # Setting the folder_id of the attachment will make it appear in Documents
        rslt['folder_id'] = self.export_wizard_id.folder_id.id
        rslt['tag_ids'] = [(6, 0, self.export_wizard_id.tag_ids.ids)]
        return rslt
