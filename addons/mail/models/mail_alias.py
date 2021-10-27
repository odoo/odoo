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
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', search='_search_display_name')
    alias_domain_id = fields.Many2one(
        'mail.alias.domain', string='Alias Domain', ondelete='restrict',
        default=lambda self: self.env.company.alias_domain_id)
    alias_domain = fields.Char('Alias domain name', related='alias_domain_id.name')
    # target: create / update
    alias_model_id = fields.Many2one('ir.model', 'Aliased Model', required=True, ondelete="cascade",
                                     help="The model (Odoo Document Kind) to which this alias "
                                          "corresponds. Any incoming email that does not reply to an "
                                          "existing record will cause the creation of a new record "
                                          "of this model (e.g. a Project Task)",
                                      # hack to only allow selecting mail_thread models (we might
                                      # (have a few false positives, though)
                                      domain="[('field_id.name', '=', 'message_ids')]")
    alias_user_id = fields.Many2one('res.users', 'Owner', default=lambda self: self.env.user,
                                    help="The owner of records created upon receiving emails on this alias. "
                                         "If this field is not set the system will attempt to find the right owner "
                                         "based on the sender (From) address, or will use the Administrator account "
                                         "if no system user is found for that address.")
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
    alias_parent_thread_id = fields.Integer('Parent Record Thread ID', help="ID of the parent record holding the alias (example: project holding the task creation alias)")
    # incoming configuration (mailgateway)
    alias_contact = fields.Selection([
        ('everyone', 'Everyone'),
        ('partners', 'Authenticated Partners'),
        ('followers', 'Followers only')], default='everyone',
        string='Alias Contact Security', required=True,
        help="Policy to post a message on the document using the mailgateway.\n"
             "- everyone: everyone can post\n"
             "- partners: only authenticated partners\n"
             "- followers: only followers of the related document or members of following channels\n")
    alias_incoming_local = fields.Boolean('Local-part based incoming detection', default=False)
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

    def init(self):
        """Make sure there aren't multiple records for the same name and alias
        domain. Not in _sql_constraint because COALESCE is not supported for
        PostgreSQL constraint. """
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS mail_alias_name_domain_unique
            ON mail_alias (alias_name, COALESCE(alias_domain_id, 0))
        """)

    @api.constrains('alias_domain_id', 'alias_force_thread_id', 'alias_parent_model_id',
                    'alias_parent_thread_id', 'alias_model_id')
    def _check_alias_domain_id_mc(self):
        """ Check for invalid alias domains based on company configuration.
        When having a parent record and/or updating an existing record alias
        domain should match the one used on the related record. """
        for alias in self.filtered('alias_domain_id'):
            # parent record (owner, like 'project' for aliases creating 'task')
            if alias.alias_parent_model_id and alias.alias_parent_thread_id:
                ParentModel = self.env[alias.alias_parent_model_id.model]
                parent_company_field = ParentModel._mail_get_company_field()
                if parent_company_field:
                    parent = ParentModel.browse(alias.alias_parent_thread_id)
                    if parent[parent_company_field] and parent[parent_company_field].alias_domain_id != alias.alias_domain_id:
                        raise ValidationError(_("Invalid company setup"))
            # updated record (like posting on a 'mail.group'')
            if alias.alias_model_id and alias.alias_force_thread_id:
                Model = self.env[alias.alias_model_id.model]
                aliased_company_field = Model._mail_get_company_field()
                if aliased_company_field:
                    aliased = Model.browse(alias.alias_force_thread_id)
                    if aliased[aliased_company_field] and aliased[aliased_company_field].alias_domain_id != alias.alias_domain_id:
                        raise ValidationError(_("Invalid company setup"))

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

    @api.constrains('alias_name', 'alias_domain_id')
    def _check_alias_name_and_domain_clash(self):
        for alias in self.filtered('alias_name'):
            if alias.alias_name in {alias.alias_domain_id.bounce, alias.alias_domain_id.catchall}:
                raise ValidationError(
                    _('The e-mail alias %(matching_alias_name)s is already used as %(alias_duplicate)s alias. Please choose another alias.',
                      matching_alias_name=alias.display_name,
                      alias_duplicate=_('catchall') if alias.alias_name == alias.alias_domain_id.catchall else _('bounce'))
                )

    @api.depends('alias_domain', 'alias_name')
    def _compute_display_name(self):
        """ Return the mail alias display alias_name, including the catchall
        domain if found otherwise "Inactive Alias". e.g.`jobs@mail.odoo.com`
        or `jobs` or 'Inactive Alias' """
        for record in self:
            if record.alias_name and record.alias_domain:
                record.display_name = f"{record.alias_name}@{record.alias_domain}"
            elif record.alias_name:
                record.display_name = record.alias_name
            else:
                record.display_name = _("Inactive Alias")

    def _search_display_name(self, operator, operand):
        """ When searching for 'sales@mycompany.com' we should search on name
        being sales and domain being mycompany.com. """
        if '@' in operand:
            left_part, right_part = operand.split('@', 1)
            return ['&', ('alias_name', operator, left_part), ('alias_domain_id.name', operator, right_part)]
        return ['|', ('alias_name', operator, operand), ('alias_domain_id.name', operator, operand)]

    @api.depends('alias_name')
    def _compute_alias_domain(self):
        self.alias_domain = self._alias_get_catchall_domain()

    @api.depends('alias_contact', 'alias_defaults', 'alias_model_id')
    def _compute_alias_status(self):
        """Reset alias_status to "not_tested" when fields, that can be the source of an error, are modified."""
        self.alias_status = 'not_tested'

    @api.depends('alias_contact', 'alias_defaults', 'alias_model_id')
    def _compute_alias_status(self):
        """Reset alias_status to "not_tested" when fields, that can be the source of an error, are modified."""
        self.alias_status = 'not_tested'

    @api.model_create_multi
    def create(self, vals_list):
        """ Creates mail.alias records according to the values provided in
        ``vals`` but sanitize 'alais_name' by replacing certain unsafe
        characters.

        Also pre-check uniqueness of (alias_name, alias_domain_id) to raise
        an human readable error instead of hard SQL constraint. """
        alias_names, alias_domains = [], self.env['mail.alias.domain']
        for vals in vals_list:
            if vals.get('alias_name'):
                vals['alias_name'] = self._sanitize_alias_name(vals['alias_name'])
                alias_names.append(vals['alias_name'])
            vals['alias_domain_id'] = vals.get('alias_domain_id') or self.env.company.alias_domain_id.id
            alias_domains |= alias_domains.browse(vals['alias_domain_id'])

        if alias_names:
            self._raise_for_alias_name_and_domain_uniqueness(alias_names, alias_domains)

        return super().create(vals_list)

    def write(self, vals):
        """ Check for uniqueness of (alias_name, alias_domain_id) to raise
        an human readable error instead of hard SQL constraint. """
        if vals.get('alias_name') and self.ids:
            if len(self) > 1:
                raise UserError(
                    _('Email alias %(alias_name)s cannot be used on %(count)d records at the same time. Please update records one by one.',
                      alias_name=vals['alias_name'], count=len(self))
                )
            vals['alias_name'] = self._sanitize_alias_name(vals['alias_name'])

        alias_names, alias_domains = [], self.alias_domain_id
        if vals.get('alias_name'):
            alias_names = [vals['alias_name']]
        elif not 'alias_name' in vals and vals.get('alias_domain_id'):
            # avoid checking when writing the same value
            if [vals['alias_domain_id']] != self.alias_domain_id.ids:
                alias_names = self.filtered('alias_name').mapped('alias_name')
        if vals.get('alias_domain_id'):
            alias_domains = self.env['mail.alias.domain'].browse(vals['alias_domain_id'])
        if alias_names:
            self._raise_for_alias_name_and_domain_uniqueness(alias_names, alias_domains)

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

    def _raise_for_alias_name_and_domain_uniqueness(self, alias_names, alias_domains):
        """ Check for existing (alias_name, alias_domain) and raise in case of
        duplicates. An SQL constraint exists, this method is mainly done to
        send better errors to the user. """
        # matches existing alias
        domain = [
            ('alias_name', 'in', alias_names),
            ('alias_domain_id', 'in', alias_domains.ids)
        ]
        existing = self.search(domain, limit=1)

        if existing.alias_parent_model_id and existing.alias_parent_thread_id:
            # If parent model and parent thread ID both are set, display document name also in the warning
            document_name = self.env[existing.alias_parent_model_id.model].sudo().browse(existing.alias_parent_thread_id).display_name
            raise UserError(
                _('Alias %(matching_name)s (%(matching_id)s) is already used by the %(document_name)s %(model_name)s. Choose another value for %(current_id)s or change it on the other document.',
                  current_id=self.ids if self else _('your alias'),
                  matching_id=existing.id,
                  matching_name=existing.display_name,
                  document_name=document_name,
                  model_name=existing.alias_parent_model_id.name)
            )
        if existing:
            raise UserError(
                _('Alias %(matching_name)s (%(matching_id)s) is already linked with %(alias_model_name)s. Choose another value for %(current_id)s or change it on the linked model.',
                  current_id=self.ids if self else _('your alias'),
                  matching_id=existing.id,
                  matching_name=existing.display_name,
                  alias_model_name=existing.alias_model_id.name)
            )

    @api.model
    def _sanitize_alias_name(self, name):
        """ Cleans and sanitizes the alias name """
        sanitized_name = remove_accents(name).lower().split('@')[0]
        sanitized_name = re.sub(r'[^\w+.]+', '-', sanitized_name)
        sanitized_name = re.sub(r'^\.+|\.+$|\.+(?=\.)', '', sanitized_name)
        sanitized_name = sanitized_name.encode('ascii', errors='replace').decode()
        return sanitized_name

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

    def _get_alias_bounced_body_fallback(self, message_dict):
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
        """Get the body of the bounced email returned when the alias is misconfigured (ex.: error in alias_defaults).

        :param message_dict: dictionary of mail values
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

    def _get_alias_bounced_body(self, message_dict):
        """Get the body of the email return in case of bounced email.

        :param message_dict: dictionary of mail values
        """
        lang_author = False
        if message_dict.get('author_id'):
            try:
                lang_author = self.env['res.partner'].browse(message_dict['author_id']).lang
            except:
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

    def _set_alias_invalid(self, message, message_dict):
        """Set alias status to invalid and create bounce message to the sender
        and the alias responsible.

        This method must be called when a message received on the alias has
        caused an error due to the mis-configuration of the alias.

        :param EmailMessage message: email message that has caused the error
        :param dict message_dict: dictionary of mail values
        """
        self.ensure_one()
        self.alias_status = 'invalid'
        body = self._get_alias_invalid_body(message_dict)
        self.env['mail.thread']._routing_create_bounce_email(message_dict['email_from'], body, message,
                                                             references=message_dict['message_id'],
                                                             # add the alias responsible as recipient if set
                                                             recipient_ids=self.alias_user_id.partner_id.ids)
