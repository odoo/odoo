# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import itertools
import logging

from odoo import _, api, fields, models, tools, Command
from odoo.exceptions import ValidationError, UserError
from odoo.tools import is_html_empty
from odoo.tools.safe_eval import safe_eval, time

_logger = logging.getLogger(__name__)


class MailTemplate(models.Model):
    "Templates for sending email"
    _name = "mail.template"
    _inherit = ['mail.render.mixin', 'template.reset.mixin']
    _description = 'Email Templates'
    _order = 'user_id,name,id'

    _unrestricted_rendering = True

    @api.model
    def default_get(self, fields):
        res = super(MailTemplate, self).default_get(fields)
        if res.get('model'):
            res['model_id'] = self.env['ir.model']._get(res.pop('model')).id
        return res

    # description
    name = fields.Char('Name', translate=True)
    description = fields.Text(
        'Template description', translate=True,
        help="This field is used for internal description of the template's usage.")
    active = fields.Boolean(default=True)
    template_category = fields.Selection(
        [('base_template', 'Base Template'),
         ('hidden_template', 'Hidden Template'),
         ('custom_template', 'Custom Template')],
         compute="_compute_template_category", search="_search_template_category")
    model_id = fields.Many2one('ir.model', 'Applies to')
    model = fields.Char('Related Document Model', related='model_id.model', index=True, store=True, readonly=True)
    subject = fields.Char('Subject', translate=True, prefetch=True, help="Subject (placeholders may be used here)")
    email_from = fields.Char('From',
                             help="Sender address (placeholders may be used here). If not set, the default "
                                  "value will be the author's email alias if configured, or email address.")
    user_id = fields.Many2one('res.users', string='User', domain="[('share', '=', False)]", help='The template belongs to this user')
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
    body_html = fields.Html(
        'Body', render_engine='qweb', render_options={'post_process': True},
        prefetch=True, translate=True, sanitize=False)
    attachment_ids = fields.Many2many('ir.attachment', 'email_template_attachment_rel', 'email_template_id',
                                      'attachment_id', 'Attachments',
                                      help="You may attach files to this template, to be added to all "
                                           "emails created from this template")
    report_template_ids = fields.Many2many(
        'ir.actions.report', relation='mail_template_ir_actions_report_rel',
        column1='mail_template_id',
        column2='ir_actions_report_id',
        string='Dynamic Reports',
        domain="[('model', '=', model)]")
    email_layout_xmlid = fields.Char('Email Notification Layout', copy=False)
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
    is_template_editor = fields.Boolean(compute="_compute_is_template_editor")

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

    @api.depends_context('uid')
    def _compute_is_template_editor(self):
        self.is_template_editor = self.user_has_groups('mail.group_mail_template_editor')

    @api.depends('active', 'description')
    def _compute_template_category(self):
        """ Base templates (or master templates) are active templates having
        a description and an XML ID. User defined templates (no xml id),
        templates without description or archived templates are not
        base templates anymore. """
        deactivated = self.filtered(lambda template: not template.active)
        if deactivated:
            deactivated.template_category = 'hidden_template'
        remaining = self - deactivated
        if remaining:
            template_external_ids = remaining.get_external_id()
            for template in remaining:
                if bool(template_external_ids[template.id]) and template.description:
                    template.template_category = 'base_template'
                elif bool(template_external_ids[template.id]):
                    template.template_category = 'hidden_template'
                else:
                    template.template_category = 'custom_template'

    @api.model
    def _search_template_category(self, operator, value):
        if operator in ['in', 'not in'] and isinstance(value, list):
            value_templates = self.env['mail.template'].search([]).filtered(
                lambda t: t.template_category in value
            )
            return [('id', operator, value_templates.ids)]

        if operator in ['=', '!='] and isinstance(value, str):
            value_templates = self.env['mail.template'].search([]).filtered(
                lambda t: t.template_category == value
            )
            return [('id', 'in' if operator == "=" else 'not in', value_templates.ids)]

        raise NotImplementedError(_('Operation not supported'))

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    def _fix_attachment_ownership(self):
        for record in self:
            record.attachment_ids.write({'res_model': record._name, 'res_id': record.id})
        return self

    def _check_abstract_models(self, vals_list):
        model_names = self.sudo().env['ir.model'].browse(filter(None, (
            vals.get('model_id') for vals in vals_list
        ))).mapped('model')
        for model in model_names:
            if self.env[model]._abstract:
                raise ValidationError(_('You may not define a template on an abstract model: %s', model))

    @api.model_create_multi
    def create(self, vals_list):
        self._check_abstract_models(vals_list)
        return super().create(vals_list)\
            ._fix_attachment_ownership()

    def write(self, vals):
        self._check_abstract_models([vals])
        super().write(vals)
        self._fix_attachment_ownership()
        return True

    def open_delete_confirmation_modal(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': self._name,
            'target': 'new',
            'view_id': self.env.ref('mail.mail_template_view_form_confirm_delete').id,
            'context': {'dialog_size': 'medium'},
            'name': _('Confirmation'),
        }

    def unlink(self):
        self.unlink_action()
        return super(MailTemplate, self).unlink()

    def cancel_unlink(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': self._name,
            'target': 'new',
            'context': {'dialog_size': 'large'},
        }

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
            context = {
                'default_composition_mode': 'mass_mail',
                'default_model': template.model,
                'default_template_id' : template.id,
            }
            button_name = _('Send Mail (%s)', template.name)
            action = ActWindow.create({
                'name': button_name,
                'type': 'ir.actions.act_window',
                'res_model': 'mail.compose.message',
                'context': repr(context),
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

    def _generate_template_attachments(self, res_ids, render_fields,
                                       render_results=None):
        """ Render attachments of template 'self', returning values for records
        given by 'res_ids'. Note that ``report_template_ids`` returns values for
        'attachments', as we have a list of tuple (report_name, base64 value)
        for those reports. It is considered as being the job of callers to
        transform those attachments into valid ``ir.attachment`` records.

        :param list res_ids: list of record IDs on which template is rendered;
        :param list render_fields: list of fields to render on template which
          are specific to attachments, e.g. attachment_ids or report_template_ids;
        :param dict render_results: res_ids-based dictionary of render values.
          For each res_id, a dict of values based on render_fields is given

        :return: updated (or new) render_results;
        """
        self.ensure_one()
        if render_results is None:
            render_results = {}

        # generating reports is done on a per-record basis, better ensure cache
        # is filled up to avoid rendering and browsing in a loop
        if res_ids and 'report_template_ids' in render_fields and self.report_template_ids:
            self.env[self.model].browse(res_ids)

        for res_id in res_ids:
            values = render_results.setdefault(res_id, {})

            # link template attachments directly
            if 'attachment_ids' in render_fields:
                values['attachment_ids'] = self.attachment_ids.ids

            # generate attachments (reports)
            if 'report_template_ids' in render_fields and self.report_template_ids:
                for report in self.report_template_ids:
                    # generate content
                    if report.report_type in ['qweb-html', 'qweb-pdf']:
                        report_content, report_format = self.env['ir.actions.report']._render_qweb_pdf(report, [res_id])
                    else:
                        render_res = self.env['ir.actions.report']._render(report, [res_id])
                        if not render_res:
                            raise UserError(_('Unsupported report type %s found.', report.report_type))
                        report_content, report_format = render_res
                    report_content = base64.b64encode(report_content)
                    # generate name
                    if report.print_report_name:
                        report_name = safe_eval(
                            report.print_report_name,
                            {
                                'object': self.env[self.model].browse(res_id),
                                'time': time,
                            }
                        )
                    else:
                        report_name = _('Report')
                    extension = "." + report_format
                    if not report_name.endswith(extension):
                        report_name += extension
                    values.setdefault('attachments', []).append((report_name, report_content))
            elif 'report_template_ids' in render_fields:
                values['attachments'] = []

        # hook for attachments-specific computation, used currently only for accounting
        if hasattr(self.env[self.model], '_process_attachments_for_template_post'):
            records_attachments = self.env[self.model].browse(res_ids)._process_attachments_for_template_post(self)
            for res_id, additional_attachments in records_attachments.items():
                if not additional_attachments:
                    continue
                if additional_attachments.get('attachment_ids'):
                    render_results[res_id].setdefault('attachment_ids', []).extend(additional_attachments['attachment_ids'])
                if additional_attachments.get('attachments'):
                    render_results[res_id].setdefault('attachments', []).extend(additional_attachments['attachments'])

        return render_results

    def _generate_template_recipients(self, res_ids, render_fields,
                                      find_or_create_partners=False,
                                      render_results=None):
        """ Render recipients of the template 'self', returning values for records
        given by 'res_ids'. Default values can be generated instead of the template
        values if requested by template (see 'use_default_to' field). Email fields
        ('email_cc', 'email_to') are transformed into partners if requested
        (finding or creating partners). 'partner_to' field is transformed into
        'partner_ids' field.

        Note: for performance reason, information from records are transferred to
        created partners no matter the company. For example, if we have a record of
        company A and one of B with the same email and no related partner, a partner
        will be created with company A or B but populated with information from the 2
        records. So some info might be leaked from one company to the other through
        the partner.

        :param list res_ids: list of record IDs on which template is rendered;
        :param list render_fields: list of fields to render on template which
          are specific to recipients, e.g. email_cc, email_to, partner_to);
        :param boolean find_or_create_partners: transform emails into partners
          (calling ``find_or_create`` on partner model);
        :param dict render_results: res_ids-based dictionary of render values.
          For each res_id, a dict of values based on render_fields is given;

        :return: updated (or new) render_results. It holds a 'partner_ids' key
          holding partners given by ``_message_get_default_recipients`` and/or
          generated based on 'partner_to'. If ``find_or_create_partners`` is
          False emails are present, otherwise they are included as partners
          contained in ``partner_ids``.
        """
        self.ensure_one()
        if render_results is None:
            render_results = {}
        ModelSudo = self.env[self.model].with_prefetch(res_ids).sudo()

        # if using default recipients -> ``_message_get_default_recipients`` gives
        # values for email_to, email_cc and partner_ids
        if self.use_default_to and self.model:
            default_recipients = ModelSudo.browse(res_ids)._message_get_default_recipients()
            for res_id, recipients in default_recipients.items():
                render_results.setdefault(res_id, {}).update(recipients)
        # render fields dynamically which generates recipients
        else:
            for field in set(render_fields) & {'email_cc', 'email_to', 'partner_to'}:
                generated_field_values = self._render_field(field, res_ids)
                for res_id in res_ids:
                    render_results.setdefault(res_id, {})[field] = generated_field_values[res_id]

        # create partners from emails if asked to
        if find_or_create_partners:
            res_id_to_company = {}
            if self.model and 'company_id' in ModelSudo._fields:
                for read_record in ModelSudo.browse(res_ids).read(['company_id']):
                    company_id = read_record['company_id'][0] if read_record['company_id'] else False
                    res_id_to_company[read_record['id']] = company_id

            all_emails = []
            email_to_res_ids = {}
            email_to_company = {}
            for res_id in res_ids:
                record_values = render_results.setdefault(res_id, {})
                mails = tools.email_split(record_values.pop('email_to', '')) + \
                        tools.email_split(record_values.pop('email_cc', ''))
                all_emails += mails
                record_company = res_id_to_company.get(res_id)
                for mail in mails:
                    email_to_res_ids.setdefault(mail, []).append(res_id)
                    if record_company:
                        email_to_company[mail] = record_company

            if all_emails:
                customers_information = ModelSudo.browse(res_ids)._get_customer_information()
                partners = self.env['res.partner']._find_or_create_from_emails(
                    all_emails,
                    additional_values={
                        email: {
                            'company_id': email_to_company.get(email),
                            **customers_information.get(email, {}),
                        }
                        for email in itertools.chain(all_emails, [False])
                    })
                for original_email, partner in zip(all_emails, partners):
                    if not partner:
                        continue
                    for res_id in email_to_res_ids[original_email]:
                        render_results[res_id].setdefault('partner_ids', []).append(partner.id)

        # update 'partner_to' rendered value to 'partner_ids'
        all_partner_to = {
            pid
            for record_values in render_results.values()
            for pid in self._parse_partner_to(record_values.get('partner_to', ''))
        }
        existing_pids = set()
        if all_partner_to:
            existing_pids = set(self.env['res.partner'].sudo().browse(list(all_partner_to)).exists().ids)
        for res_id, record_values in render_results.items():
            partner_to = record_values.pop('partner_to', '')
            if partner_to:
                tpl_partner_ids = set(self._parse_partner_to(partner_to)) & existing_pids
                record_values.setdefault('partner_ids', []).extend(tpl_partner_ids)

        return render_results

    def _generate_template_scheduled_date(self, res_ids, render_results=None):
        """ Render scheduled date based on template 'self'. Specific parsing is
        done to ensure value matches ORM expected value: UTC but without
        timezone set in value.

        :param list res_ids: list of record IDs on which template is rendered;
        :param dict render_results: res_ids-based dictionary of render values.
          For each res_id, a dict of values based on render_fields is given;

        :return: updated (or new) render_results;
        """
        self.ensure_one()
        if render_results is None:
            render_results = {}

        scheduled_dates = self._render_field('scheduled_date', res_ids)
        for res_id in res_ids:
            scheduled_date = self._process_scheduled_date(scheduled_dates.get(res_id))
            render_results.setdefault(res_id, {})['scheduled_date'] = scheduled_date

        return render_results

    def _generate_template_static_values(self, res_ids, render_fields, render_results=None):
        """ Return values based on template 'self'. Those are not rendered nor
        dynamic, just static values used for configuration of emails.

        :param list res_ids: list of record IDs on which template is rendered;
        :param list render_fields: list of fields to render, currently limited
          to a subset (i.e. auto_delete, mail_server_id, model, res_id);
        :param dict render_results: res_ids-based dictionary of render values.
          For each res_id, a dict of values based on render_fields is given;

        :return: updated (or new) render_results;
        """
        self.ensure_one()
        if render_results is None:
            render_results = {}

        for res_id in res_ids:
            values = render_results.setdefault(res_id, {})

            # technical settings
            if 'auto_delete' in render_fields:
                values['auto_delete'] = self.auto_delete
            if 'email_layout_xmlid' in render_fields:
                values['email_layout_xmlid'] = self.email_layout_xmlid
            if 'mail_server_id' in render_fields:
                values['mail_server_id'] = self.mail_server_id.id
            if 'model' in render_fields:
                values['model'] = self.model
            if 'res_id' in render_fields:
                values['res_id'] = res_id or False

        return render_results

    def _generate_template(self, res_ids, render_fields,
                           find_or_create_partners=False):
        """ Render values from template 'self' on records given by 'res_ids'.
        Those values are generally used to create a mail.mail or a mail.message.
        Model of records is the one defined on template.

        :param list res_ids: list of record IDs on which template is rendered;
        :param list render_fields: list of fields to render on template;
        :param boolean find_or_create_partners: transform emails into partners
          (see ``_generate_template_recipients``);

        :returns: a dict of (res_ids, values) where values contains all rendered
          fields asked in ``render_fields``. Asking for attachments adds an
          'attachments' key using the format [(report_name, data)] where data
          is base64 encoded. Asking for recipients adds a 'partner_ids' key.
          Note that 2many fields contain a list of IDs, not commands.
        """
        self.ensure_one()
        render_fields_set = set(render_fields)
        fields_specific = {
            'attachment_ids',  # attachments
            'email_cc',  # recipients
            'email_to',  # recipients
            'partner_to',  # recipients
            'report_template_ids',  # attachments
            'scheduled_date',  # specific
            # not rendered (static)
            'auto_delete',
            'email_layout_xmlid',
            'mail_server_id',
            'model',
            'res_id',
        }

        render_results = {}
        for _lang, (template, template_res_ids) in self._classify_per_lang(res_ids).items():
            # render fields not rendered by sub methods
            fields_torender = {
                field for field in render_fields_set
                if field not in fields_specific
            }
            for field in fields_torender:
                generated_field_values = template._render_field(
                    field, template_res_ids
                )
                for res_id, field_value in generated_field_values.items():
                    render_results.setdefault(res_id, {})[field] = field_value

            # render recipients
            if render_fields_set & {'email_cc', 'email_to', 'partner_to'}:
                template._generate_template_recipients(
                    template_res_ids, render_fields_set,
                    render_results=render_results,
                    find_or_create_partners=find_or_create_partners
                )

            # render scheduled_date
            if 'scheduled_date' in render_fields_set:
                template._generate_template_scheduled_date(
                    template_res_ids,
                    render_results=render_results
            )

            # add values static for all res_ids
            template._generate_template_static_values(
                template_res_ids,
                render_fields_set,
                render_results=render_results
            )

            # generate attachments if requested
            if render_fields_set & {'attachment_ids', 'report_template_ids'}:
                template._generate_template_attachments(
                    template_res_ids,
                    render_fields_set,
                    render_results=render_results
                )

        return render_results

    @classmethod
    def _parse_partner_to(cls, partner_to):
        return [
            int(pid.strip()) for pid in partner_to.split(',')
            if (pid and pid.strip().isdigit())
        ]

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
        values = self._generate_template(
            [res_id],
            ('attachment_ids',
             'auto_delete',
             'body_html',
             'email_cc',
             'email_from',
             'email_to',
             'mail_server_id',
             'model',
             'partner_to',
             'reply_to',
             'report_template_ids',
             'res_id',
             'scheduled_date',
             'subject',
            )
        )[res_id]
        values['recipient_ids'] = [Command.link(pid) for pid in values.get('partner_ids', list())]
        values['attachment_ids'] = [Command.link(aid) for aid in values.get('attachment_ids', list())]
        values.update(email_values or {})
        attachment_ids = values.pop('attachment_ids', [])
        attachments = values.pop('attachments', [])
        # add a protection against void email_from
        if 'email_from' in values and not values.get('email_from'):
            values.pop('email_from')
        # encapsulate body
        email_layout_xmlid = email_layout_xmlid or self.email_layout_xmlid
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
