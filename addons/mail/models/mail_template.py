# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging

from odoo import _, api, fields, models, tools, Command
from odoo.exceptions import UserError
from odoo.tools import is_html_empty

_logger = logging.getLogger(__name__)


class MailTemplate(models.Model):
    "Templates for sending email"
    _name = "mail.template"
    _inherit = ['mail.render.mixin', 'template.reset.mixin']
    _description = 'Email Templates'
    _order = 'name'

    _unrestricted_rendering = True

    @api.model
    def default_get(self, fields):
        res = super(MailTemplate, self).default_get(fields)
        if res.get('model'):
            res['model_id'] = self.env['ir.model']._get(res.pop('model')).id
        return res

    # description
    name = fields.Char('Name', translate=True)
    model_id = fields.Many2one('ir.model', 'Applies to')
    model = fields.Char('Related Document Model', related='model_id.model', index=True, store=True, readonly=True)
    subject = fields.Char('Subject', translate=True, prefetch=True, help="Subject (placeholders may be used here)")
    email_from = fields.Char('From',
                             help="Sender address (placeholders may be used here). If not set, the default "
                                  "value will be the author's email alias if configured, or email address.")
    # recipients
    use_default_to = fields.Boolean(
        'Default recipients',
        help="Default recipients of the record:\n"
             "- partner (using id on a partner or the partner_id field) OR\n"
             "- email (using email_from or email field)")
    email_to = fields.Char('To (Emails)', help="Comma-separated recipient addresses (placeholders may be used here)")
    partner_to = fields.Char('To (Partners)',
                             help="Comma-separated ids of recipient partners (placeholders may be used here)")
    email_cc = fields.Char('Cc', help="Carbon copy recipients (placeholders may be used here)")
    reply_to = fields.Char('Reply To', help="Email address to which replies will be redirected when sending emails in mass; only used when the reply is not logged in the original discussion thread.")
    # content
    body_html = fields.Html('Body', render_engine='qweb', translate=True, prefetch=True, sanitize=False)
    attachment_ids = fields.Many2many('ir.attachment', 'email_template_attachment_rel', 'email_template_id',
                                      'attachment_id', 'Attachments',
                                      help="You may attach files to this template, to be added to all "
                                           "emails created from this template")
    report_name = fields.Char('Report Filename', translate=True, prefetch=True,
                              help="Name to use for the generated report file (may contain placeholders)\n"
                                   "The extension can be omitted and will then come from the report type.")
    report_template = fields.Many2one('ir.actions.report', 'Optional report to print and attach')
    # options
    mail_server_id = fields.Many2one('ir.mail_server', 'Outgoing Mail Server', readonly=False,
                                     help="Optional preferred server for outgoing mails. If not set, the highest "
                                          "priority one will be used.")
    scheduled_date = fields.Char('Scheduled Date', help="If set, the queue manager will send the email after the date. If not set, the email will be send as soon as possible. You can use dynamic expression.")
    auto_delete = fields.Boolean(
        'Auto Delete', default=True,
        help="This option permanently removes any track of email after it's been sent, including from the Technical menu in the Settings, in order to preserve storage space of your Odoo database.")
    # contextual action
    ref_ir_act_window = fields.Many2one('ir.actions.act_window', 'Sidebar action', readonly=True, copy=False,
                                        help="Sidebar action to make this template available on records "
                                             "of the related document model")

    # access
    can_write = fields.Boolean(compute='_compute_can_write',
                               help='The current user can edit the template.')

    # Overrides of mail.render.mixin
    @api.depends('model')
    def _compute_render_model(self):
        for template in self:
            template.render_model = template.model

    @api.depends_context('uid')
    def _compute_can_write(self):
        writable_templates = self._filter_access_rules('write')
        for template in self:
            template.can_write = template in writable_templates

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    def _fix_attachment_ownership(self):
        for record in self:
            record.attachment_ids.write({'res_model': record._name, 'res_id': record.id})
        return self

    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)\
            ._fix_attachment_ownership()

    def write(self, vals):
        super().write(vals)
        self._fix_attachment_ownership()
        return True

    def unlink(self):
        self.unlink_action()
        return super(MailTemplate, self).unlink()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {},
                       name=_("%s (copy)", self.name))
        return super(MailTemplate, self).copy(default=default)

    def unlink_action(self):
        for template in self:
            if template.ref_ir_act_window:
                template.ref_ir_act_window.unlink()
        return True

    def create_action(self):
        ActWindow = self.env['ir.actions.act_window']
        view = self.env.ref('mail.email_compose_message_wizard_form')

        for template in self:
            button_name = _('Send Mail (%s)', template.name)
            action = ActWindow.create({
                'name': button_name,
                'type': 'ir.actions.act_window',
                'res_model': 'mail.compose.message',
                'context': "{'default_composition_mode': 'mass_mail', 'default_template_id' : %d, 'default_use_template': True}" % (template.id),
                'view_mode': 'form,tree',
                'view_id': view.id,
                'target': 'new',
                'binding_model_id': template.model_id.id,
            })
            template.write({'ref_ir_act_window': action.id})

        return True

    # ------------------------------------------------------------
    # MESSAGE/EMAIL VALUES GENERATION
    # ------------------------------------------------------------

    def generate_recipients(self, results, res_ids):
        """Generates the recipients of the template. Default values can ben generated
        instead of the template values if requested by template or context.
        Emails (email_to, email_cc) can be transformed into partners if requested
        in the context. """
        self.ensure_one()

        if self.use_default_to or self._context.get('tpl_force_default_to'):
            records = self.env[self.model].browse(res_ids).sudo()
            default_recipients = records._message_get_default_recipients()
            for res_id, recipients in default_recipients.items():
                results[res_id].pop('partner_to', None)
                results[res_id].update(recipients)

        records_company = None
        if self._context.get('tpl_partners_only') and self.model and results and 'company_id' in self.env[self.model]._fields:
            records = self.env[self.model].browse(results.keys()).read(['company_id'])
            records_company = {rec['id']: (rec['company_id'][0] if rec['company_id'] else None) for rec in records}

        for res_id, values in results.items():
            partner_ids = values.get('partner_ids', list())
            if self._context.get('tpl_partners_only'):
                mails = tools.email_split(values.pop('email_to', '')) + tools.email_split(values.pop('email_cc', ''))
                Partner = self.env['res.partner']
                if records_company:
                    Partner = Partner.with_context(default_company_id=records_company[res_id])
                for mail in mails:
                    partner = Partner.find_or_create(mail)
                    partner_ids.append(partner.id)
            partner_to = values.pop('partner_to', '')
            if partner_to:
                # placeholders could generate '', 3, 2 due to some empty field values
                tpl_partner_ids = [int(pid) for pid in partner_to.split(',') if pid]
                partner_ids += self.env['res.partner'].sudo().browse(tpl_partner_ids).exists().ids
            results[res_id]['partner_ids'] = partner_ids
        return results

    def generate_email(self, res_ids, fields):
        """Generates an email from the template for given the given model based on
        records given by res_ids.

        :param res_id: id of the record to use for rendering the template (model
                       is taken from template definition)
        :returns: a dict containing all relevant fields for creating a new
                  mail.mail entry, with one extra key ``attachments``, in the
                  format [(report_name, data)] where data is base64 encoded.
        """
        self.ensure_one()
        multi_mode = True
        if isinstance(res_ids, int):
            res_ids = [res_ids]
            multi_mode = False

        results = dict()
        for lang, (template, template_res_ids) in self._classify_per_lang(res_ids).items():
            for field in fields:
                generated_field_values = template._render_field(
                    field, template_res_ids,
                    post_process=(field == 'body_html')
                )
                for res_id, field_value in generated_field_values.items():
                    results.setdefault(res_id, dict())[field] = field_value
            # compute recipients
            if any(field in fields for field in ['email_to', 'partner_to', 'email_cc']):
                results = template.generate_recipients(results, template_res_ids)
            # update values for all res_ids
            for res_id in template_res_ids:
                values = results[res_id]
                if values.get('body_html'):
                    values['body'] = tools.html_sanitize(values['body_html'])
                # if asked in fields to return, parse generated date into tz agnostic UTC as expected by ORM
                scheduled_date = values.pop('scheduled_date', None)
                if 'scheduled_date' in fields and scheduled_date:
                    parsed_datetime = self.env['mail.mail']._parse_scheduled_datetime(scheduled_date)
                    values['scheduled_date'] = parsed_datetime.replace(tzinfo=None) if parsed_datetime else False

                # technical settings
                values.update(
                    mail_server_id=template.mail_server_id.id or False,
                    auto_delete=template.auto_delete,
                    model=template.model,
                    res_id=res_id or False,
                    attachment_ids=[attach.id for attach in template.attachment_ids],
                )

            # Add report in attachments: generate once for all template_res_ids
            if template.report_template:
                for res_id in template_res_ids:
                    attachments = []
                    report_name = template._render_field('report_name', [res_id])[res_id]
                    report = template.report_template
                    report_service = report.report_name

                    if report.report_type in ['qweb-html', 'qweb-pdf']:
                        result, report_format = self.env['ir.actions.report']._render_qweb_pdf(report, [res_id])
                    else:
                        res = self.env['ir.actions.report']._render(report, [res_id])
                        if not res:
                            raise UserError(_('Unsupported report type %s found.', report.report_type))
                        result, report_format = res

                    # TODO in trunk, change return format to binary to match message_post expected format
                    result = base64.b64encode(result)
                    if not report_name:
                        report_name = 'report.' + report_service
                    ext = "." + report_format
                    if not report_name.endswith(ext):
                        report_name += ext
                    attachments.append((report_name, result))
                    results[res_id]['attachments'] = attachments

        return multi_mode and results or results[res_ids[0]]

    # ------------------------------------------------------------
    # EMAIL
    # ------------------------------------------------------------

    def _send_check_access(self, res_ids):
        records = self.env[self.model].browse(res_ids)
        records.check_access_rights('read')
        records.check_access_rule('read')

    def send_mail(self, res_id, force_send=False, raise_exception=False, email_values=None,
                  email_layout_xmlid=False):
        """ Generates a new mail.mail. Template is rendered on record given by
        res_id and model coming from template.

        :param int res_id: id of the record to render the template
        :param bool force_send: send email immediately; otherwise use the mail
            queue (recommended);
        :param dict email_values: update generated mail with those values to further
            customize the mail;
        :param str email_layout_xmlid: optional notification layout to encapsulate the
            generated email;
        :returns: id of the mail.mail that was created """

        # Grant access to send_mail only if access to related document
        self.ensure_one()
        self._send_check_access([res_id])

        Attachment = self.env['ir.attachment']  # TDE FIXME: should remove default_type from context

        # create a mail_mail based on values, without attachments
        values = self.generate_email(
            res_id,
            ['subject', 'body_html',
             'email_from',
             'email_cc', 'email_to', 'partner_to', 'reply_to',
             'auto_delete', 'scheduled_date']
        )
        values['recipient_ids'] = [Command.link(pid) for pid in values.get('partner_ids', list())]
        values['attachment_ids'] = [Command.link(aid) for aid in values.get('attachment_ids', list())]
        values.update(email_values or {})
        attachment_ids = values.pop('attachment_ids', [])
        attachments = values.pop('attachments', [])
        # add a protection against void email_from
        if 'email_from' in values and not values.get('email_from'):
            values.pop('email_from')
        # encapsulate body
        if email_layout_xmlid and values['body_html']:
            record = self.env[self.model].browse(res_id)
            model = self.env['ir.model']._get(record._name)

            if self.lang:
                lang = self._render_lang([res_id])[res_id]
                model = model.with_context(lang=lang)

            template_ctx = {
                # message
                'message': self.env['mail.message'].sudo().new(dict(body=values['body_html'], record_name=record.display_name)),
                'subtype': self.env['mail.message.subtype'].sudo(),
                # record
                'model_description': model.display_name,
                'record': record,
                'record_name': False,
                'subtitles': False,
                # user / environment
                'company': 'company_id' in record and record['company_id'] or self.env.company,
                'email_add_signature': False,
                'signature': '',
                'website_url': '',
                # tools
                'is_html_empty': is_html_empty,
            }
            body = model.env['ir.qweb']._render(email_layout_xmlid, template_ctx, minimal_qcontext=True, raise_if_not_found=False)
            if not body:
                _logger.warning(
                    'QWeb template %s not found when sending template %s. Sending without layout.',
                    email_layout_xmlid,
                    self.name
                )

            values['body_html'] = self.env['mail.render.mixin']._replace_local_links(body)

        mail = self.env['mail.mail'].sudo().create(values)

        # manage attachments
        for attachment in attachments:
            attachment_data = {
                'name': attachment[0],
                'datas': attachment[1],
                'type': 'binary',
                'res_model': 'mail.message',
                'res_id': mail.mail_message_id.id,
            }
            attachment_ids.append((4, Attachment.create(attachment_data).id))
        if attachment_ids:
            mail.write({'attachment_ids': attachment_ids})

        if force_send:
            mail.send(raise_exception=raise_exception)
        return mail.id  # TDE CLEANME: return mail + api.returns ?

    # ------------------------------------------------------------
    # neutralize
    # ------------------------------------------------------------

    def _neutralize(self):
        super()._neutralize()
        self.flush_model()
        self.invalidate_model()
        self.env.cr.execute("UPDATE mail_template SET mail_server_id=NULL")
