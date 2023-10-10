# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import re

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import is_html_empty, remove_accents

# see rfc5322 section 3.2.3
atext = r"[a-zA-Z0-9!#$%&'*+\-/=?^_`{|}~]"
dot_atom_text = re.compile(r"^%s+(\.%s+)*$" % (atext, atext))


class Alias(models.Model):
    """A Mail Alias is a mapping of an email address with a given Odoo Document
       model. It is used by Odoo's mail gateway when processing incoming emails
       sent to the system. If the recipient address (To) of the message matches
       a Mail Alias, the message will be either processed following the rules
       of that alias. If the message is a reply it will be attached to the
       existing discussion on the corresponding record, otherwise a new
       record of the corresponding model will be created.

       This is meant to be used in combination with a catch-all email configuration
       on the company's mail server, so that as soon as a new mail.alias is
       created, it becomes immediately usable and Odoo will accept email for it.
     """
    _name = 'mail.alias'
    _description = "Email Aliases"
    _rec_name = 'alias_name'
    _order = 'alias_model_id, alias_name'

    # email definition
    alias_name = fields.Char(
        'Alias Name', copy=False,
        help="The name of the email alias, e.g. 'jobs' if you want to catch emails for <jobs@example.odoo.com>")
    alias_domain = fields.Char('Alias domain', compute='_compute_alias_domain')
    # target: create / update
    alias_model_id = fields.Many2one('ir.model', 'Aliased Model', required=True, ondelete="cascade",
                                     help="The model (Odoo Document Kind) to which this alias "
                                          "corresponds. Any incoming email that does not reply to an "
                                          "existing record will cause the creation of a new record "
                                          "of this model (e.g. a Project Task)",
                                      # hack to only allow selecting mail_thread models (we might
                                      # (have a few false positives, though)
                                      domain="[('field_id.name', '=', 'message_ids')]")
    alias_defaults = fields.Text('Default Values', required=True, default='{}',
                                 help="A Python dictionary that will be evaluated to provide "
                                      "default values when creating new records for this alias.")
    alias_force_thread_id = fields.Integer(
        'Record Thread ID',
        help="Optional ID of a thread (record) to which all incoming messages will be attached, even "
             "if they did not reply to it. If set, this will disable the creation of new records completely.")
    # owner
    alias_parent_model_id = fields.Many2one(
        'ir.model', 'Parent Model',
        help="Parent model holding the alias. The model holding the alias reference "
             "is not necessarily the model given by alias_model_id "
             "(example: project (parent_model) and task (model))")
    alias_parent_thread_id = fields.Integer(
        'Parent Record Thread ID',
        help="ID of the parent record holding the alias (example: project holding the task creation alias)")
    # incoming configuration (mailgateway)
    alias_contact = fields.Selection(
        [
            ('everyone', 'Everyone'),
            ('partners', 'Authenticated Partners'),
            ('followers', 'Followers only')
        ], default='everyone',
        string='Alias Contact Security', required=True,
        help="Policy to post a message on the document using the mailgateway.\n"
             "- everyone: everyone can post\n"
             "- partners: only authenticated partners\n"
             "- followers: only followers of the related document or members of following channels\n")
    alias_bounced_content = fields.Html(
        "Custom Bounced Message", translate=True,
        help="If set, this content will automatically be sent out to unauthorized users instead of the default message.")
    alias_status = fields.Selection(
        [
            ('not_tested', 'Not Tested'),
            ('valid', 'Valid'),
            ('invalid', 'Invalid'),
        ], compute='_compute_alias_status', store=True,
        help='Alias status assessed on the last message received.')

    _sql_constraints = [
        ('alias_unique', 'UNIQUE(alias_name)', 'Unfortunately this email alias is already used, please choose a unique one')
    ]

    @api.constrains('alias_name')
    def _check_alias_is_ascii(self):
        """ The local-part ("display-name" <local-part@domain>) of an
            address only contains limited range of ascii characters.
            We DO NOT allow anything else than ASCII dot-atom formed
            local-part. Quoted-string and internationnal characters are
            to be rejected. See rfc5322 sections 3.4.1 and 3.2.3
        """
        for alias in self.filtered('alias_name'):
            if not dot_atom_text.match(alias.alias_name):
                raise ValidationError(
                    _("You cannot use anything else than unaccented latin characters in the alias address %(alias_name)s.",
                      alias_name=alias.alias_name)
                )

    @api.constrains('alias_defaults')
    def _check_alias_defaults(self):
        for alias in self:
            try:
                dict(ast.literal_eval(alias.alias_defaults))
            except Exception as e:
                raise ValidationError(
                    _('Invalid expression, it must be a literal python dictionary definition e.g. "{\'field\': \'value\'}"')
                ) from e

    @api.depends('alias_domain', 'alias_name')
    def _compute_display_name(self):
        """Return the mail alias display alias_name, including the implicit
           mail catchall domain if exists from config otherwise "New Alias".
           e.g. `jobs@mail.odoo.com` or `jobs` or 'New Alias'
        """
        for record in self:
            if record.alias_name and record.alias_domain:
                record.display_name = f"{record.alias_name}@{record.alias_domain}"
            elif record.alias_name:
                record.display_name = record.alias_name
            else:
                record.display_name = _("Inactive Alias")

    @api.depends('alias_name')
    def _compute_alias_domain(self):
        self.alias_domain = self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")

    @api.depends('alias_contact', 'alias_defaults', 'alias_model_id')
    def _compute_alias_status(self):
        """Reset alias_status to "not_tested" when fields, that can be the source of an error, are modified."""
        self.alias_status = 'not_tested'

    @api.model_create_multi
    def create(self, vals_list):
        """ Creates email.alias records according to the values provided in
        ``vals`` with 1 alteration:

          * ``alias_name`` value may be cleaned by replacing certain unsafe
            characters;

        :raise UserError: if given alias_name is already assigned or there are
        duplicates in given vals_list;
        """
        alias_names = [self._sanitize_alias_name(vals.get('alias_name')) for vals in vals_list]
        self._check_unique(alias_names)
        for vals, alias_name in zip(vals_list, alias_names):
            vals['alias_name'] = alias_name
        return super().create(vals_list)

    def write(self, vals):
        """ Raise UserError with a meaningfull message instead of letting the
        unicity constraint give its error. """
        if 'alias_name' in vals:
            vals['alias_name'] = self._sanitize_alias_name(vals['alias_name'])
        if vals.get('alias_name') and self.ids:
            self._check_unique([vals['alias_name']])
            if len(self) > 1:
                raise UserError(
                    _('Email alias %(alias_name)s cannot be used on %(count)d records at the same time. Please update records one by one.',
                      alias_name=vals['alias_name'], count=len(self))
                )
        return super().write(vals)

    def _clean_and_check_mail_catchall_allowed_domains(self, value):
        """ The purpose of this system parameter is to avoid the creation
        of records from incoming emails with a domain != alias_domain
        but that have a pattern matching an internal mail.alias . """
        value = [domain.strip().lower() for domain in value.split(',') if domain.strip()]
        if not value:
            raise ValidationError(
                _("Value for `mail.catchall.domain.allowed` cannot be validated.\n"
                  "It should be a comma separated list of domains e.g. example.com,example.org.")
            )
        return ",".join(value)

    def _check_unique(self, sanitized_names, skip_icp_keys=None):
        """ Check unicity constraint won't be raised, otherwise raise a UserError
        with a complete error message. Also check unicity against alias config
        parameters.

        :param list sanitized_names: a list of names (considered as sanitized
          and ready to be sent to DB);
        """
        valid_names = list(filter(None, sanitized_names))

        # list itself should be unique obviously
        seen = set()
        dupes = [name for name in valid_names if name in seen or seen.add(name)]
        if dupes:
            raise UserError(
                _('Email aliases %(alias_name)s cannot be used on several records at the same time. Please update records one by one.',
                  alias_name=', '.join(dupes))
            )

        alias_domain = self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")
        icp_to_check = dict(
            (icp_key, self.env["ir.config_parameter"].sudo().get_param(icp_key))
            for icp_key in {'mail.bounce.alias', 'mail.catchall.alias'}
            if icp_key not in (skip_icp_keys or ())
        )
        icp_label_by_key = {
            'mail.bounce.alias': _('bounce'),
            'mail.catchall.alias': _('catchall'),
        }

        # matches catchall or bounce alias
        for sanitized_name in valid_names:
            for icp_key, icp_value in icp_to_check.items():
                if icp_value and sanitized_name == icp_value:
                    matching_alias_name = f'{sanitized_name}@{alias_domain}' if alias_domain else sanitized_name
                    raise UserError(
                        _('The e-mail alias %(matching_alias_name)s is already used as %(alias_duplicate)s alias. Please choose another alias.',
                          matching_alias_name=matching_alias_name,
                          alias_duplicate=icp_label_by_key[icp_key])
                    )

        # matches existing alias
        matching_alias = self.env['mail.alias']
        if valid_names:
            domain = [('alias_name', 'in', valid_names)]
            if self:
                domain += [('id', 'not in', self.ids)]
            matching_alias = self.search(domain, limit=1)
        if not matching_alias:
            return
        if matching_alias.alias_parent_model_id and matching_alias.alias_parent_thread_id:
            # If parent model and parent thread ID both are set, display document name also in the warning
            document_name = self.env[matching_alias.alias_parent_model_id.model].sudo().browse(matching_alias.alias_parent_thread_id).display_name
            raise UserError(
                _('The e-mail alias %(matching_alias_name)s is already used by the %(document_name)s %(model_name)s. Choose another alias or change it on the other document.',
                  matching_alias_name=matching_alias.display_name,
                  document_name=document_name,
                  model_name=matching_alias.alias_parent_model_id.name)
                )
        raise UserError(
            _('The e-mail alias %(matching_alias_name)s is already linked with %(alias_model_name)s. Choose another alias or change it on the linked model.',
              matching_alias_name=matching_alias.display_name,
              alias_model_name=matching_alias.alias_model_id.name)
        )

    @api.model
    def _sanitize_alias_name(self, name):
        """ Cleans and sanitizes the alias name """
        sanitized_name = name.strip() if name else ''
        if sanitized_name:
            sanitized_name = remove_accents(sanitized_name).lower().split('@')[0]
            # cannot start and end with dot
            sanitized_name = re.sub(r'^\.+|\.+$|\.+(?=\.)', '', sanitized_name)
            # subset of allowed characters
            sanitized_name = re.sub(r'[^\w!#$%&\'*+\-/=?^_`{|}~.]+', '-', sanitized_name)
            sanitized_name = sanitized_name.encode('ascii', errors='replace').decode()
        if not sanitized_name.strip():
            return False
        return sanitized_name

    @api.model
    def _is_encodable(self, alias_name, charset='ascii'):
        """ Check if alias_name is encodable. Standard charset is ascii, as
        UTF-8 requires a specific extension. Not recommended for outgoing
        aliases. 'remove_accents' is performed as sanitization process of
        the name will do it anyway. """
        try:
            remove_accents(alias_name).encode(charset)
        except UnicodeEncodeError:
            return False
        return True

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def open_document(self):
        if not self.alias_model_id or not self.alias_force_thread_id:
            return False
        return {
            'view_mode': 'form',
            'res_model': self.alias_model_id.model,
            'res_id': self.alias_force_thread_id,
            'type': 'ir.actions.act_window',
        }

    def open_parent_document(self):
        if not self.alias_parent_model_id or not self.alias_parent_thread_id:
            return False
        return {
            'view_mode': 'form',
            'res_model': self.alias_parent_model_id.model,
            'res_id': self.alias_parent_thread_id,
            'type': 'ir.actions.act_window',
        }

    # ------------------------------------------------------------
    # MAIL GATEWAY
    # ------------------------------------------------------------

    def _get_alias_bounced_body(self, message_dict):
        """Get the body of the email return in case of bounced email when the
        alias does not accept incoming email e.g. contact is not allowed.

        :param dict message_dict: dictionary holding parsed message variables

        :return: HTML to use as email body
        """
        lang_author = False
        if message_dict.get('author_id'):
            try:
                lang_author = self.env['res.partner'].browse(message_dict['author_id']).lang
            except Exception:
                pass

        if lang_author:
            self = self.with_context(lang=lang_author)

        if not is_html_empty(self.alias_bounced_content):
            body = self.alias_bounced_content
        else:
            body = self._get_alias_bounced_body_fallback(message_dict)
        return self.env['ir.qweb']._render('mail.mail_bounce_alias_security', {
            'body': body,
            'message': message_dict
        }, minimal_qcontext=True)

    def _get_alias_bounced_body_fallback(self, message_dict):
        """ Default body of bounced emails. See '_get_alias_bounced_body' """
        contact_description = self._get_alias_contact_description()
        default_email = self.env.company.partner_id.email_formatted if self.env.company.partner_id.email else self.env.company.name
        content = Markup(
            _("""The message below could not be accepted by the address %(alias_display_name)s.
                 Only %(contact_description)s are allowed to contact it.<br /><br />
                 Please make sure you are using the correct address or contact us at %(default_email)s instead."""
              )
        ) % {
            'alias_display_name': self.display_name,
            'contact_description': contact_description,
            'default_email': default_email,
        }
        return Markup('<p>%(header)s,<br /><br />%(content)s<br /><br />%(regards)s</p>') % {
            'content': content,
            'header': _('Dear Sender'),
            'regards': _('Kind Regards'),
        }

    def _get_alias_contact_description(self):
        if self.alias_contact == 'partners':
            return _('addresses linked to registered partners')
        return _('some specific addresses')

    def _get_alias_invalid_body(self, message_dict):
        """Get the body of the bounced email returned when the alias is incorrectly
        configured e.g. error in alias_defaults.

        :param dict message_dict: dictionary holding parsed message variables

        :return: HTML to use as email body
        """
        content = Markup(
            _("""The message below could not be accepted by the address %(alias_display_name)s.
Please try again later or contact %(company_name)s instead."""
              )
        ) % {
            'alias_display_name': self.display_name,
            'company_name': self.env.company.name,
        }
        return self.env['ir.qweb']._render('mail.mail_bounce_alias_security', {
            'body': Markup('<p>%(header)s,<br /><br />%(content)s<br /><br />%(regards)s</p>') % {
                'content': content,
                'header': _('Dear Sender'),
                'regards': _('Kind Regards'),
            },
            'message': message_dict
        }, minimal_qcontext=True)

    def _alias_bounce_incoming_email(self, message, message_dict, set_invalid=True):
        """Set alias status to invalid and create bounce message to the sender
        and the alias responsible.

        This method must be called when a message received on the alias has
        caused an error due to the mis-configuration of the alias.

        :param EmailMessage message: email message that is invalid and is about
          to bounce;
        :param dict message_dict: dictionary holding parsed message variables
        :param bool set_invalid: set alias as invalid, to be done notably if
          bounce is considered as coming from a configuration error instead of
          being rejected due to alias rules;
        """
        self.ensure_one()
        if set_invalid:
            self.alias_status = 'invalid'
            body = self._get_alias_invalid_body(message_dict)
        else:
            body = self._get_alias_bounced_body(message_dict)
        self.env['mail.thread']._routing_create_bounce_email(
            message_dict['email_from'], body, message,
            references=message_dict['message_id'],
            # add the alias creator as recipient if set
            recipient_ids=self.create_uid.partner_id.ids if self.create_uid.active else [],
        )
