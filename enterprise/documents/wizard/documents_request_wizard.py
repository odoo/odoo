# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.tools.misc import clean_context


class RequestWizard(models.TransientModel):
    _name = "documents.request_wizard"
    _description = "Document Request"

    name = fields.Char(required=True)
    requestee_id = fields.Many2one('res.partner', required=True, string="Owner")
    partner_id = fields.Many2one('res.partner', string="Contact")

    activity_type_id = fields.Many2one('mail.activity.type',
                                       string="Activity type",
                                       default=lambda self: self.env.ref('documents.mail_documents_activity_data_md',
                                                                         raise_if_not_found=False),
                                       required=True,
                                       domain="[('category', '=', 'upload_file')]")

    tag_ids = fields.Many2many('documents.tag', string="Tags")
    folder_id = fields.Many2one('documents.document',
                                domain="[('type', '=', 'folder'), ('shortcut_document_id', '=', False)]",
                                string="Folder")

    res_model = fields.Char('Resource Model')
    res_id = fields.Integer('Resource ID')

    activity_note = fields.Html(string="Message")
    activity_date_deadline_range = fields.Integer(string='Due Date In', default=30)
    activity_date_deadline_range_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Due type', default='days')

    @api.onchange('activity_type_id')
    def _on_activity_type_change(self):
        if self.activity_type_id:
            if not self.tag_ids:
                self.tag_ids = self.activity_type_id.tag_ids
            if not self.folder_id:
                self.folder_id = self.activity_type_id.folder_id
            if not self.requestee_id:
                self.requestee_id = self.activity_type_id.default_user_id.partner_id

    def request_document(self):
        self.ensure_one()
        document = self.env['documents.document'].create({
            'name': self.name,
            'folder_id': self.folder_id.id,
            'tag_ids': [(6, 0, self.tag_ids.ids if self.tag_ids else [])],
            'owner_id': self.env.user.id,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'requestee_partner_id': self.requestee_id.id,
            'res_model': self.res_model,
            'res_id': self.res_id,
        })

        activity_vals = {
            'user_id': self.requestee_id.user_ids[0].id if self.requestee_id.user_ids else self.env.user.id,
            'note': self.activity_note,
            'activity_type_id': self.activity_type_id.id if self.activity_type_id else False,
            'summary': self.name
        }

        if self.activity_date_deadline_range > 0:
            activity_vals['date_deadline'] = fields.Date.context_today(self) + relativedelta(
                **{self.activity_date_deadline_range_type: self.activity_date_deadline_range})

        request_by_mail = self.requestee_id and self.create_uid not in self.requestee_id.user_ids
        activity = document.with_context(mail_activity_quick_update=request_by_mail).activity_schedule(**activity_vals)
        document.request_activity_id = activity

        # Access rights: either user edit with expiration if the requestee has a user or access_via_link=edit otherwise
        # Note that when uploaded, access_via_link will be set to view automatically (if it was set to edit)
        if self.requestee_id.user_ids:
            document.action_update_access_rights('none', partners={
                self.env.user.partner_id.id: ('edit', False),
                self.requestee_id.id: ('edit', datetime.combine(activity.date_deadline, datetime.max.time())),
            })
        else:
            document.access_via_link = 'edit'
            document.action_update_access_rights('none', partners={
                self.env.user.partner_id.id: ('edit', False)
            })
        request_template = self.env.ref('documents.mail_template_document_request', raise_if_not_found=False)
        if request_template:
            document.with_context(clean_context(self.env.context)).message_mail_with_source(request_template)

        return document
