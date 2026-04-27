# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, models, fields, _
from odoo.osv import expression


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def _prepare_next_activity_values(self):
        vals = super()._prepare_next_activity_values()
        current_activity_type = self.activity_type_id
        next_activity_type = current_activity_type.triggered_next_type_id

        if current_activity_type.category == 'upload_file' and self.res_model == 'documents.document' and next_activity_type.category == 'upload_file':
            existing_document = self.env['documents.document'].search([('request_activity_id', '=', self.id)], limit=1)
            if 'summary' not in vals:
                vals['summary'] = self.summary or _('Upload file request')
            new_doc_request = self.env['documents.document'].create({
                'owner_id': existing_document.owner_id.id,
                'folder_id': next_activity_type.folder_id.id if next_activity_type.folder_id else existing_document.folder_id.id,
                'tag_ids': [(6, 0, next_activity_type.tag_ids.ids)],
                'name': vals['summary'],
            })
            vals['res_id'] = new_doc_request.id
        return vals

    def _action_done(self, feedback=False, attachment_ids=None):
        if not self:
            return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)
        documents = self.env['documents.document'].search([('request_activity_id', 'in', self.ids)])
        document_without_attachment = documents.filtered(lambda d: not d.attachment_id)
        if document_without_attachment and not feedback:
            feedback = _("Document Request: %(name)s Uploaded by: %(user)s",
                         name=documents[0].name, user=self.env.user.name)
        messages, next_activities = super(MailActivity, self.with_context(no_document=True))._action_done(
            feedback=feedback, attachment_ids=attachment_ids)
        # Downgrade access link role from edit to view if necessary (if the requestee didn't have a user at the request
        # time, we previously granted him edit access by setting access_via_link to edit on the document).
        documents.filtered(lambda document: document.access_via_link == 'edit').access_via_link = 'view'
        # Remove request information on the document
        documents.requestee_partner_id = False
        documents.request_activity_id = False
        # Attachment must be set after documents.request_activity_id is set to False to prevent document write to
        # trigger an action_done.
        if attachment_ids and document_without_attachment:
            document_without_attachment.attachment_id = attachment_ids[0]
        return messages, next_activities

    @api.model_create_multi
    def create(self, vals_list):
        activities = super().create(vals_list)
        upload_activities = activities.filtered(lambda act: act.activity_category == 'upload_file')

        # link back documents and activities
        upload_documents_activities = upload_activities.filtered(lambda act: act.res_model == 'documents.document')
        if upload_documents_activities:
            documents = self.env['documents.document'].browse(upload_documents_activities.mapped('res_id'))
            for document, activity in zip(documents, upload_documents_activities):
                if not document.request_activity_id:
                    document.request_activity_id = activity.id

        # create underlying documents if related record is not a document
        doc_vals = [{
            'res_model': activity.res_model,
            'res_id': activity.res_id,
            'owner_id': activity.activity_type_id.default_user_id.id or self.env.user.id,
            'folder_id': activity.activity_type_id.folder_id.id,
            'tag_ids': [(6, 0, activity.activity_type_id.tag_ids.ids)],
            'name': activity.summary or activity.res_name or 'upload file request',
            'request_activity_id': activity.id,
        } for activity in upload_activities.filtered(
            lambda act: act.res_model != 'documents.document' and act.activity_type_id.folder_id
        )]
        if doc_vals:
            self.env['documents.document'].sudo().create(doc_vals)
        return activities

    def write(self, vals):
        write_result = super().write(vals)
        if 'date_deadline' not in vals or not (
                act_on_docs := self.filtered(lambda activity: activity.res_model == 'documents.document')):
            return write_result
        # Update expiration access of the requestee when updating the related request activity deadline
        document_requestee_partner_ids = self.env['documents.document'].search_read([
            ('id', 'in', act_on_docs.mapped('res_id')),
            ('requestee_partner_id', '!=', False),
            ('request_activity_id', 'in', self.ids),
        ], ['requestee_partner_id'])
        new_expiration_date = datetime.combine(self[0].date_deadline, datetime.max.time())
        self.env['documents.access'].search(expression.OR([[
            ('document_id', '=', document_requestee_partner_id['id']),
            ('partner_id', '=', document_requestee_partner_id['requestee_partner_id'][0]),
            ('expiration_date', '<', new_expiration_date),
        ] for document_requestee_partner_id in document_requestee_partner_ids
        ])).expiration_date = new_expiration_date
