# -*- coding: utf-8 -*-

import base64
import io
import logging
import re
from ast import literal_eval
from collections import OrderedDict

import requests
from PyPDF2 import PdfFileReader
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression
from odoo.tools import image_process
from odoo.tools.mimetypes import get_extension
from odoo.tools.misc import clean_context
from odoo.addons.mail.tools import link_preview

from .documents_facet import N_FACET_COLORS

_logger = logging.getLogger(__name__)


def _sanitize_file_extension(extension):
    """ Remove leading and trailing spacing + Remove leading "." """
    return re.sub(r'^[\s.]+|\s+$', '', extension)


class Document(models.Model):
    _name = 'documents.document'
    _description = 'Document'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _order = 'id desc'
    _systray_view = 'activity'

    # Attachment
    attachment_id = fields.Many2one('ir.attachment', ondelete='cascade', auto_join=True, copy=False)
    attachment_name = fields.Char('Attachment Name', related='attachment_id.name', readonly=False)
    attachment_type = fields.Selection(string='Attachment Type', related='attachment_id.type', readonly=False)
    is_editable_attachment = fields.Boolean(default=False, help='True if we can edit the link attachment.')
    is_multipage = fields.Boolean('Is considered multipage', compute='_compute_is_multipage', store=True)
    datas = fields.Binary(related='attachment_id.datas', related_sudo=True, readonly=False, prefetch=False)
    raw = fields.Binary(related='attachment_id.raw', related_sudo=True, readonly=False, prefetch=False)
    file_extension = fields.Char('File Extension', copy=True, store=True, readonly=False,
                                 compute='_compute_file_extension', inverse='_inverse_file_extension')
    file_size = fields.Integer(related='attachment_id.file_size', store=True)
    checksum = fields.Char(related='attachment_id.checksum')
    mimetype = fields.Char(related='attachment_id.mimetype')
    res_model = fields.Char('Resource Model', compute="_compute_res_record", inverse="_inverse_res_model", store=True)
    res_id = fields.Many2oneReference('Resource ID', compute="_compute_res_record", inverse="_inverse_res_model", store=True, model_field="res_model")
    res_name = fields.Char('Resource Name', compute="_compute_res_name", compute_sudo=True)
    index_content = fields.Text(related='attachment_id.index_content')
    description = fields.Text('Attachment Description', related='attachment_id.description', readonly=False)

    # Versioning
    previous_attachment_ids = fields.Many2many('ir.attachment', string="History")

    # Document
    name = fields.Char('Name', copy=True, store=True, compute='_compute_name_and_preview', inverse='_inverse_name')
    active = fields.Boolean(default=True, string="Active")
    thumbnail = fields.Binary(readonly=False, store=True, attachment=True, compute='_compute_thumbnail')
    thumbnail_status = fields.Selection([
            ('present', 'Present'), # Document has a thumbnail
            ('error', 'Error'), # Error when generating the thumbnail
        ], compute="_compute_thumbnail_status", store=True, readonly=False,
    )
    url = fields.Char('URL', index=True, size=1024, tracking=True)
    url_preview_image = fields.Char('URL Preview Image', store=True, compute='_compute_name_and_preview')
    res_model_name = fields.Char(compute='_compute_res_model_name', index=True)
    type = fields.Selection([('url', 'URL'), ('binary', 'File'), ('empty', 'Request')],
                            string='Type', required=True, store=True, default='empty', change_default=True,
                            compute='_compute_type')
    favorited_ids = fields.Many2many('res.users', string="Favorite of")
    is_favorited = fields.Boolean(compute='_compute_is_favorited', inverse='_inverse_is_favorited')
    tag_ids = fields.Many2many('documents.tag', 'document_tag_rel', string="Tags")
    partner_id = fields.Many2one('res.partner', string="Contact", tracking=True)
    owner_id = fields.Many2one('res.users', default=lambda self: self.env.user.id, string="Owner",
                               tracking=True)
    available_rule_ids = fields.Many2many('documents.workflow.rule', compute='_compute_available_rules',
                                          string='Available Rules')
    lock_uid = fields.Many2one('res.users', string="Locked by")
    is_locked = fields.Boolean(compute="_compute_is_locked", string="Locked")
    create_share_id = fields.Many2one('documents.share', help='Share used to create this document')
    request_activity_id = fields.Many2one('mail.activity')

    # Folder
    folder_id = fields.Many2one('documents.folder',
                                string="Workspace",
                                ondelete="restrict",
                                tracking=True,
                                required=True,
                                index=True)
    company_id = fields.Many2one('res.company', string='Company', related='folder_id.company_id', readonly=True)
    group_ids = fields.Many2many('res.groups', string="Access Groups", readonly=True,
                                 help="This attachment will only be available for the selected user groups",
                                 related='folder_id.group_ids')

    _sql_constraints = [
        ('attachment_unique', 'unique (attachment_id)', "This attachment is already a document"),
    ]

    @api.depends('name', 'type')
    def _compute_file_extension(self):
        for record in self:
            if record.type != 'binary':
                record.file_extension = False
            elif record.name:
                record.file_extension = _sanitize_file_extension(get_extension(record.name.strip())) or False

    def _inverse_file_extension(self):
        for record in self:
            record.file_extension = _sanitize_file_extension(record.file_extension) if record.file_extension else False

    @api.depends('attachment_id', 'attachment_id.name', 'url')
    def _compute_name_and_preview(self):
        request_session = requests.Session()
        for record in self:
            if record.attachment_id:
                record.name = record.attachment_id.name
                record.url_preview_image = False
            elif record.url:
                preview = link_preview.get_link_preview_from_url(record.url, request_session)
                if not preview:
                    continue
                if preview.get('og_title'):
                    record.name = preview['og_title']
                if preview.get('og_image'):
                    record.url_preview_image = preview['og_image']

    def _inverse_name(self):
        for record in self:
            if record.attachment_id:
                record.attachment_name = record.name

    @api.depends('datas', 'mimetype')
    def _compute_is_multipage(self):
        for document in self:
            # external computation to be extended
            document.is_multipage = bool(document._get_is_multipage())  # None => False

    @api.depends('attachment_id', 'attachment_id.res_model', 'attachment_id.res_id')
    def _compute_res_record(self):
        for record in self:
            attachment = record.attachment_id
            if attachment:
                record.res_model = attachment.res_model
                record.res_id = attachment.res_id

    @api.depends('attachment_id', 'res_model', 'res_id')
    def _compute_res_name(self):
        for record in self:
            if record.attachment_id:
                record.res_name = record.attachment_id.res_name
            elif record.res_id and record.res_model:
                record.res_name = self.env[record.res_model].browse(record.res_id).display_name
            else:
                record.res_name = False

    def _inverse_res_model(self):
        for record in self:
            attachment = record.attachment_id.with_context(no_document=True)
            if attachment:
                # Avoid inconsistency in the data, write both at the same time.
                # In case a check_access is done between res_id and res_model modification,
                # an access error can be received. (Mail causes this check_access)
                attachment.sudo().write({'res_model': record.res_model, 'res_id': record.res_id})

    @api.depends('checksum')
    def _compute_thumbnail(self):
        for record in self:
            if record.mimetype == 'application/pdf':
                # Thumbnails of pdfs are generated by the client. To force the generation, we invalidate the thumbnail.
                record.thumbnail = False
            else:
                try:
                    record.thumbnail = base64.b64encode(image_process(record.raw, size=(200, 140), crop='center'))
                except (UserError, TypeError):
                    record.thumbnail = False

    @api.depends("thumbnail")
    def _compute_thumbnail_status(self):
        domain = [
            ('res_model', '=', self._name),
            ('res_field', '=', 'thumbnail'),
            ('res_id', 'in', self.ids),
        ]
        documents_with_thumbnail = set(res['res_id'] for res in self.env['ir.attachment'].sudo().search_read(domain, ['res_id']))
        for document in self:
            if document.mimetype == 'application/pdf':
                # As the thumbnail invalidation is not propagated to the status, we invalid it as well.
                document.thumbnail_status = False
            else:
                document.thumbnail_status = document.id in documents_with_thumbnail and 'present'

    @api.depends('attachment_type', 'url')
    def _compute_type(self):
        for record in self:
            record.type = 'empty'
            if record.attachment_id:
                record.type = 'binary'
            elif record.url:
                record.type = 'url'

    def get_deletion_delay(self):
        return int(self.env['ir.config_parameter'].sudo().get_param('documents.deletion_delay', '30'))

    def _get_is_multipage(self):
        """Whether the document can be considered multipage, if able to determine.

        :return: `None` if mimetype not handled, `False` if single page or error occurred, `True` otherwise.
        :rtype: bool | None
        """
        if self.mimetype not in ('application/pdf', 'application/pdf;base64'):
            return None
        stream = io.BytesIO(base64.b64decode(self.datas))
        try:
            return PdfFileReader(stream, strict=False).numPages > 1
        except AttributeError:
            raise  # If PyPDF's API changes and the `numPages` property isn't there anymore, not if its computation fails.
        except Exception:  # noqa: BLE001
            _logger.warning('Impossible to count pages in %r. It could be due to a malformed document or a '
                            '(possibly known) issue within PyPDF2.', self.name, exc_info=True)
            return False

    def _get_models(self, domain):
        """
        Return the names of the models to which the attachments are attached.

        :param domain: the domain of the _read_group on documents.
        :return: a list of model data, the latter being a dict with the keys
            'id' (technical name),
            'name' (display name) and
            '__count' (how many attachments with that domain).
        """
        not_a_file = []
        not_attached = []
        models = []
        groups = self._read_group(domain, ['res_model'], ['__count'])
        for res_model, count in groups:
            if not res_model:
                not_a_file.append({
                    'id': res_model,
                    'display_name': _('Not a file'),
                    '__count': count,
                })
            elif res_model == 'documents.document':
                not_attached.append({
                    'id': res_model,
                    'display_name': _('Not attached'),
                    '__count': count,
                })
            else:
                models.append({
                    'id': res_model,
                    'display_name': self.env['ir.model']._get(res_model).display_name,
                    '__count': count,
                })
        return sorted(models, key=lambda m: m['display_name']) + not_attached + not_a_file

    @api.depends('favorited_ids')
    @api.depends_context('uid')
    def _compute_is_favorited(self):
        favorited = self.filtered(lambda d: self.env.user in d.favorited_ids)
        favorited.is_favorited = True
        (self - favorited).is_favorited = False

    def _inverse_is_favorited(self):
        unfavorited_documents = favorited_documents = self.env['documents.document'].sudo()
        for document in self:
            if self.env.user in document.favorited_ids:
                unfavorited_documents |= document
            else:
                favorited_documents |= document
        favorited_documents.write({'favorited_ids': [(4, self.env.uid)]})
        unfavorited_documents.write({'favorited_ids': [(3, self.env.uid)]})

    @api.depends('res_model')
    def _compute_res_model_name(self):
        for record in self:
            if record.res_model:
                record.res_model_name = self.env['ir.model']._get(record.res_model).display_name
            else:
                record.res_model_name = False

    @api.depends('folder_id')
    def _compute_available_rules(self):
        """
        loads the rules that can be applied to the attachment.

        """
        self.available_rule_ids = False
        folder_ids = self.mapped('folder_id.id')
        rule_domain = [('domain_folder_id', 'parent_of', folder_ids)] if folder_ids else []
        # searching rules with sudo as rules are inherited from parent folders and should be available even
        # when they come from a restricted folder.
        rules = self.env['documents.workflow.rule'].sudo().search(rule_domain)
        for rule in rules:
            domain = []
            if rule.condition_type == 'domain':
                domain = literal_eval(rule.domain) if rule.domain else []
            else:
                if rule.criteria_partner_id:
                    domain = expression.AND([[['partner_id', '=', rule.criteria_partner_id.id]], domain])
                if rule.criteria_owner_id:
                    domain = expression.AND([[['owner_id', '=', rule.criteria_owner_id.id]], domain])
                if rule.create_model:
                    domain = expression.AND([[['type', '=', 'binary']], domain])
                if rule.required_tag_ids:
                    domain = expression.AND([[['tag_ids', 'in', rule.required_tag_ids.ids]], domain])
                if rule.excluded_tag_ids:
                    domain = expression.AND([[['tag_ids', 'not in', rule.excluded_tag_ids.ids]], domain])

            folder_domain = [['folder_id', 'child_of', rule.domain_folder_id.id]]
            subset = expression.AND([[['id', 'in', self.ids]], domain, folder_domain])
            document_ids = self.env['documents.document'].search(subset)
            for document in document_ids:
                document.available_rule_ids = [(4, rule.id, False)]

    @api.constrains('url')
    def _check_url(self):
        for document in self.filtered("url"):
            if not document.url.startswith(('https://', 'http://', 'ftp://')):
                raise ValidationError(_('URL %s does not seem complete, as it does not begin with http(s):// or ftp://', document.url))

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """
        creates a new attachment from any email sent to the alias.
        The values defined in the share link upload settings are included
        in the custom values (via the alias defaults, synchronized on update)
        """
        subject = msg_dict.get('subject', '')
        if custom_values is None:
            custom_values = {}

        # Remove non existing tags to allow saving document with the mail alias
        tags = custom_values.get('tag_ids')
        if tags and isinstance(tags, (list, tuple)) and isinstance(tags[0], (list, tuple)):
            custom_values['tag_ids'] = [(tags[0][0], tags[0][1],
                                             self.env['documents.tag'].browse(tags[0][2]).exists().ids)]

        defaults = {
            'name': "Mail: %s" % subject,
            'active': False,
        }
        defaults.update(custom_values)

        return super(Document, self).message_new(msg_dict, defaults)

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *, message_type='notification', **kwargs):
        if message_type == 'email' and self.create_share_id:
            self = self.with_context(no_document=True)
        return super(Document, self).message_post(message_type=message_type, **kwargs)

    def _message_post_after_hook(self, message, msg_vals):
        """
        If the res model was an attachment and a mail, adds all the custom values of the share link
            settings to the attachments of the mail.

        """
        m2m_commands = msg_vals['attachment_ids']
        share = self.create_share_id
        if share and not self.env.context.get("no_document") or message.message_type == 'email':
            attachments = self.env['ir.attachment'].browse([x[1] for x in m2m_commands])
            documents = self.env['documents.document'].create([{
                'name': attachment.name,
                'attachment_id': attachment.id,
                'folder_id': share.folder_id.id,
                'owner_id': share.owner_id.user_ids[0].id if share.owner_id.user_ids else share.create_uid.id,
                'partner_id': share.partner_id.id or False,
                'tag_ids': [(6, 0, share.tag_ids.ids or [])],
            } for attachment in attachments])
            for (attachment, document) in zip(attachments, documents):
                attachment.write({
                    'res_model': 'documents.document',
                    'res_id': document.id,
                })
                document.message_post(body=msg_vals.get('body', ''), subject=self.name)
                if share.activity_option:
                    document.documents_set_activity(settings_record=share)

        return super(Document, self)._message_post_after_hook(message, msg_vals)

    def documents_set_activity(self, settings_record=None):
        """
        Generate an activity based on the fields of settings_record.

        :param settings_record: the record that contains the activity fields.
                    settings_record.activity_type_id (required)
                    settings_record.activity_summary
                    settings_record.activity_note
                    settings_record.activity_date_deadline_range
                    settings_record.activity_date_deadline_range_type
                    settings_record.activity_user_id
        """
        if settings_record and settings_record.activity_type_id:
            for record in self:
                activity_vals = {
                    'activity_type_id': settings_record.activity_type_id.id,
                    'summary': settings_record.activity_summary or '',
                    'note': settings_record.activity_note or '',
                }
                if settings_record.activity_date_deadline_range > 0:
                    activity_vals['date_deadline'] = fields.Date.context_today(settings_record) + relativedelta(
                        **{settings_record.activity_date_deadline_range_type: settings_record.activity_date_deadline_range})
                if settings_record._fields.get('has_owner_activity') and settings_record.has_owner_activity and record.owner_id:
                    user = record.owner_id
                elif settings_record._fields.get('activity_user_id') and settings_record.activity_user_id:
                    user = settings_record.activity_user_id
                elif settings_record._fields.get('user_id') and settings_record.user_id:
                    user = settings_record.user_id
                else:
                    user = self.env.user
                if user:
                    activity_vals['user_id'] = user.id
                record.activity_schedule(**activity_vals)

    def toggle_favorited(self):
        self.ensure_one()
        self.sudo().write({'favorited_ids': [(3 if self.env.user in self[0].favorited_ids else 4, self.env.user.id)]})

    def access_content(self):
        self.ensure_one()
        action = {
            'type': "ir.actions.act_url",
            'target': "new",
        }
        if self.url:
            action['url'] = self.url
        elif self.type == 'binary':
            action['url'] = '/documents/content/%s' % self.id
        return action

    def create_share(self):
        self.ensure_one()
        vals = {
            'type': 'ids',
            'document_ids': [(6, 0, self.ids)],
            'folder_id': self.folder_id.id,
        }
        return self.env['documents.share'].open_share_popup(vals)

    def open_resource(self):
        self.ensure_one()
        if self.res_model and self.res_id:
            view_id = self.env[self.res_model].get_formview_id(self.res_id)
            return {
                'res_id': self.res_id,
                'res_model': self.res_model,
                'type': 'ir.actions.act_window',
                'views': [[view_id, 'form']],
            }

    def toggle_lock(self):
        """
        sets a lock user, the lock user is the user who locks a file for themselves, preventing data replacement
        and archive (therefore deletion) for any user but himself.

        Members of the group documents.group_document_manager and the superuser can unlock the file regardless.
        """
        self.ensure_one()
        if self.lock_uid:
            if self.env.user == self.lock_uid or self.env.is_admin() or self.user_has_groups(
                    'documents.group_document_manager'):
                self.lock_uid = False
        else:
            self.lock_uid = self.env.uid

    def _compute_is_locked(self):
        for record in self:
            record.is_locked = record.lock_uid and not (
                    self.env.user == record.lock_uid or
                    self.env.is_admin() or
                    self.user_has_groups('documents.group_document_manager'))

    def action_archive(self):
        if not self:
            return
        active_documents = self.filtered(self._active_name)
        deletion_date = fields.Date.to_string(fields.Date.today() + relativedelta(days=self.get_deletion_delay()))
        log_message = _("This file has been sent to the trash and will be deleted forever on the %s", deletion_date)
        active_documents._message_log_batch(bodies={doc.id: log_message for doc in active_documents})
        return super().action_archive()

    def action_unarchive(self):
        if not self:
            return
        archived_documents = self.filtered(lambda record: not record[self._active_name])
        log_message = _("This file has been restored")
        archived_documents._message_log_batch(bodies={doc.id: log_message for doc in archived_documents})
        # Unarchive folders linked to archived documents
        archived_documents.folder_id.filtered(lambda folder: not folder[self._active_name]).action_unarchive()
        return super().action_unarchive()

    @api.model_create_multi
    def create(self, vals_list):
        attachments = []
        for vals in vals_list:
            keys = [key for key in vals if
                    self._fields[key].related and self._fields[key].related.split('.')[0] == 'attachment_id']
            attachment_dict = {key: vals.pop(key) for key in keys if key in vals}
            attachment = self.env['ir.attachment'].browse(vals.get('attachment_id'))

            if attachment and attachment_dict:
                attachment.write(attachment_dict)
            elif attachment_dict:
                attachment_dict.setdefault('name', vals.get('name', 'unnamed'))
                # default_res_model and default_res_id will cause unique constraints to trigger.
                attachment = self.env['ir.attachment'].with_context(clean_context(self.env.context)).create(attachment_dict)
                vals['attachment_id'] = attachment.id
            attachments.append(attachment)

        documents = super().create(vals_list)

        # this condition takes precedence during forward-port.
        for document, attachment in zip(documents, attachments):
            if (attachment and not attachment.res_id and (not attachment.res_model or attachment.res_model == 'documents.document')):
                attachment.with_context(no_document=True).write({
                    'res_model': 'documents.document',
                    'res_id': document.id})
        return documents

    def write(self, vals):
        if vals.get('folder_id') and not self.env.is_superuser():
            folder = self.env['documents.folder'].browse(vals.get('folder_id'))
            if not folder.has_write_access:
                raise AccessError(_("You don't have the right to move documents to that workspace."))

        attachment_id = vals.get('attachment_id')
        if attachment_id:
            self.ensure_one()
        for record in self:

            if record.type == 'empty' and ('datas' in vals or 'url' in vals):
                body = _("Document Request: %s Uploaded by: %s", record.name, self.env.user.name)
                record.with_context(no_document=True).message_post(body=body)

            if record.attachment_id:
                # versioning
                if attachment_id:
                    # Link the new attachment to the related record and link the previous one
                    # to the document.
                    self.env["ir.attachment"].browse(attachment_id).with_context(
                        no_document=True
                    ).write(
                        {
                            "res_model": record.res_model or "documents.document",
                            "res_id": record.res_id if record.res_model else record.id,
                        }
                    )
                    record.attachment_id.with_context(no_document=True).write(
                        {"res_model": "documents.document", "res_id": record.id}
                    )
                    if attachment_id in record.previous_attachment_ids.ids:
                        record.previous_attachment_ids = [(3, attachment_id, False)]
                    record.previous_attachment_ids = [(4, record.attachment_id.id, False)]
                if 'datas' in vals:
                    old_attachment = record.attachment_id.with_context(no_document=True).copy()
                    # removes the link between the old attachment and the record.
                    old_attachment.write({
                        'res_model': 'documents.document',
                        'res_id': record.id,
                    })
                    record.previous_attachment_ids = [(4, old_attachment.id, False)]
            elif vals.get('datas') and not vals.get('attachment_id'):
                res_model = vals.get('res_model', record.res_model or 'documents.document')
                res_id = vals.get('res_id') if vals.get('res_model') else record.res_id if record.res_model else record.id
                if res_model and res_model != 'documents.document' and not self.env[res_model].browse(res_id).exists():
                    record.res_model = res_model = 'documents.document'
                    record.res_id = res_id = record.id
                attachment = self.env['ir.attachment'].with_context(no_document=True).create({
                    'name': vals.get('name', record.name),
                    'res_model': res_model,
                    'res_id': res_id
                })
                record.attachment_id = attachment.id
                record.with_context(no_document=True)._process_activities(attachment.id)

        # pops the datas and/or the mimetype key(s) to explicitly write them in batch on the ir.attachment
        # so the mimetype is properly set. The reason was because the related keys are not written in batch
        # and because mimetype is readonly on `ir.attachment` (which prevents writing through the related).
        attachment_dict = {key: vals.pop(key) for key in ['datas', 'mimetype'] if key in vals}

        write_result = super(Document, self).write(vals)
        if attachment_dict:
            self.mapped('attachment_id').write(attachment_dict)

        if 'attachment_id' in vals:
            self.attachment_id.check('read')

        return write_result

    def _process_activities(self, attachment_id):
        self.ensure_one()
        if attachment_id and self.request_activity_id:
            feedback = _("Document Request: %s Uploaded by: %s", self.name, self.env.user.name)
            self.request_activity_id.action_feedback(feedback=feedback, attachment_ids=[attachment_id])

    @api.model
    def _pdf_split(self, new_files=None, open_files=None, vals=None):
        vals = vals or {}
        new_attachments = self.env['ir.attachment']._pdf_split(new_files=new_files, open_files=open_files)

        return self.create([
            dict(vals, attachment_id=attachment.id) for attachment in new_attachments
        ])

    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        if field_name == 'folder_id':
            enable_counters = kwargs.get('enable_counters', False)
            fields = ['display_name', 'description', 'parent_folder_id', 'has_write_access', 'company_id']
            available_folders = self.env['documents.folder'].search([])
            folder_domain = expression.OR([[('parent_folder_id', 'parent_of', available_folders.ids)], [('id', 'in', available_folders.ids)]])
            # also fetches the ancestors of the available folders to display the complete folder tree for all available folders.
            DocumentFolder = self.env['documents.folder'].sudo().with_context(hierarchical_naming=False)
            records = DocumentFolder.search_read(folder_domain, fields)

            domain_image = {}
            if enable_counters:
                model_domain = expression.AND([
                    kwargs.get('search_domain', []),
                    kwargs.get('category_domain', []),
                    kwargs.get('filter_domain', []),
                    [(field_name, '!=', False)]
                ])
                domain_image = self._search_panel_domain_image(field_name, model_domain, enable_counters)

            values_range = OrderedDict()
            for record in records:
                record_id = record['id']
                if enable_counters:
                    image_element  = domain_image.get(record_id)
                    record['__count'] = image_element['__count'] if image_element else 0
                value = record['parent_folder_id']
                record['parent_folder_id'] = value and value[0]
                values_range[record_id] = record

            if enable_counters:
                self._search_panel_global_counters(values_range, 'parent_folder_id')

            return {
                'parent_field': 'parent_folder_id',
                'values': list(values_range.values()),
            }

        return super(Document, self).search_panel_select_range(field_name)

    def _get_processed_tags(self, domain, folder_id):
        """
        sets a group color to the tags based on the order of the facets (group_id)
        recomputed each time the search_panel fetches the tags as the colors depend on the order and
        amount of tag categories. If the amount of categories exceeds the amount of colors, the color
        loops back to the first one.
        """
        tags = self.env['documents.tag']._get_tags(domain, folder_id)
        facets = list(OrderedDict.fromkeys([tag['group_id'] for tag in tags]))
        for tag in tags:
            color_index = (facets.index(tag['group_id']) % N_FACET_COLORS) + 1
            tag['color_index'] = color_index

        return tags

    @api.model
    def search_panel_select_multi_range(self, field_name, **kwargs):
        search_domain = kwargs.get('search_domain', [])
        category_domain = kwargs.get('category_domain', [])
        filter_domain = kwargs.get('filter_domain', [])

        if field_name == 'tag_ids':
            folder_id = category_domain[0][2] if len(category_domain) else False
            if folder_id:
                domain = expression.AND([
                    search_domain, category_domain, filter_domain,
                    [(field_name, '!=', False)],
                ])
                return {'values': self._get_processed_tags(domain, folder_id)}
            else:
                return {'values': []}

        elif field_name == 'res_model':
            domain = expression.AND([search_domain, category_domain])
            model_values = self._get_models(domain)

            if filter_domain:
                # fetch new counters
                domain = expression.AND([search_domain, category_domain, filter_domain])
                model_count = {
                    model['id']: model['__count']
                    for model in self._get_models(domain)
                }
                # update result with new counters
                for model in model_values:
                    model['__count'] = model_count.get(model['id'], 0)

            return {'values': model_values}

        return super(Document, self).search_panel_select_multi_range(field_name, **kwargs)

    @api.model
    def get_document_max_upload_limit(self):
        try:
            return int(self.env['ir.config_parameter'].sudo().get_param('document.max_fileupload_size', default=0))
        except Exception:
            return False

    def unlink(self):
        """Remove its folder when deleting a document to ensure we don't retain unnecessary folders in the database.

        If:
            - The folder is inactive
            - It isn't linked to any files
            - It has no child folders
        """
        removable_folders = self.folder_id.with_context({'active_test': False}).filtered(
            lambda folder: len(folder.document_ids) == 1
            and not folder.children_folder_ids
            and not folder.active
        )
        removable_attachments = self.filtered(lambda self: self.res_model != self._name).attachment_id
        res = super().unlink()
        if removable_attachments:
            removable_attachments.unlink()
        if removable_folders:
            removable_folders.unlink()
        return res

    @api.autovacuum
    def _gc_clear_bin(self):
        """Files are deleted automatically from the trash bin after the configured remaining days."""
        deletion_delay = self.get_deletion_delay()
        self.search([
            ('active', '=', False),
            ('write_date', '<=', fields.Datetime.now() - relativedelta(days=deletion_delay)),
        ], limit=1000).unlink()
