import json
from urllib.parse import urlencode

from odoo import api, fields, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    is_l10n_in_government_document = fields.Boolean(string="IN Government Document")

    @api.model
    def _l10n_in_generate_json_attachment(self, data):
        """
        Generates or updates a JSON attachment linked to a record.
        """
        attachment = self.search([
            ('res_model', '=', data['res_model']),
            ('res_id', '=', data['res_id']),
            ('name', '=', data['name']),
            ], limit=1)
        data.update({
            'raw': json.dumps(data['raw']).encode(),
            'mimetype': 'application/json',
            'is_l10n_in_government_document': True,
        })
        if attachment:
            attachment.write(data)
        else:
            attachment = self.create(data)
        return attachment

    @api.ondelete(at_uninstall=False)
    def _unlink_except_l10n_in_government_document(self):
        """
        Prevents the deletion of government related documents.
        """
        for attachment in self:
            if attachment.is_l10n_in_government_document:
                raise UserError(self.env._("You cannot delete an attachment which is sent to or received from the government."))

    def action_download_l10n_in_government_document_json(self, attachment_id):
        params = urlencode({
            'id': attachment_id,
            'download': 'true',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?' + params
        }
