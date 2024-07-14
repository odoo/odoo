# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


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
        if self and attachment_ids:
            documents = self.env['documents.document'].search([
                ('request_activity_id', 'in', self.ids),
                ('attachment_id', '=', False)
            ])
            if documents:
                # TODO: since the route `mail_attachment_upload` has been overridden to avoid having two
                # documents created when uploading an attachment through an activity, we should remove
                # the following code in master (we keep it just in case some existing documents have been
                # created with the old behavior).
                to_remove = self.env['documents.document'].search([('attachment_id', '=', attachment_ids[0])])
                if to_remove:
                    to_remove.unlink()
                if not feedback:
                    feedback = _("Document Request: %s Uploaded by: %s", documents[0].name, self.env.user.name)
                documents.write({
                    'attachment_id': attachment_ids[0],
                    'request_activity_id': False
                })

        return super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)

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
            'owner_id': activity.activity_type_id.default_user_id.id,
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
