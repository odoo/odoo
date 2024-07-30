import base64
import uuid

from odoo import fields, http, models, _


class AccountRequestedDocument(models.Model):
    _name = 'account.requested.document'
    _description = 'Accounting Requested Document(A technical model for sharing request document link)'

    name = fields.Char('Document Name')
    attachment_id = fields.Many2one('ir.attachment', help='Technical field to hold the document')
    token = fields.Char(required=True, default=lambda __: str(uuid.uuid4()), index=True, groups='base.group_user')
    full_url = fields.Char(string="URL", compute='_compute_full_url')
    request_activity_id = fields.Many2one('mail.activity')

    def _compute_full_url(self):
        for record in self:
            record.full_url = f'{record.get_base_url()}/account/request_document/{record.token}'

    def _process_uploaded_file(self, file):
        activity = self.request_activity_id
        attachment = self.env['ir.attachment'].create({
            'name': file.filename,
            'res_model': activity.res_model,
            'res_id': activity.res_id,
            'mimetype': file.content_type,
            'type': 'binary',
            'datas': base64.b64encode(file.read()),
        })
        self.attachment_id = attachment
        self._process_activity(attachment.id)

    def _process_activity(self, attachment_id):
        self.ensure_one()
        if attachment_id and self.request_activity_id:
            feedback = _("Document Requested: %(name)s , Uploaded by: %(user)s", name=self.attachment_id.name, user=http.request.env.user.name)
            self.request_activity_id \
                .with_user(self.request_activity_id.user_id) \
                .with_context(no_new_invoice=True) \
                .action_feedback(feedback=feedback, attachment_ids=[attachment_id])
