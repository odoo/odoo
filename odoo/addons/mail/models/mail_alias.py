# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import re
from collections import defaultdict
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression
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
    alias_full_name = fields.Char('Alias Email', compute='_compute_alias_full_name', store=True, index='btree_not_null')
    display_name = fields.Char(string='Display Name', compute='_compute_display_name')
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

        # in sudo, to be able to read alias_parent_model_id (ir.model)
        tocheck = self.sudo().filtered(lambda domain: domain.alias_domain_id.company_ids)
        if not tocheck:
            return

        # helpers to find owner / target models
        def _owner_model(alias):
            return alias.alias_parent_model_id.model
        def _owner_env(alias):
            return self.env[_owner_model(alias)]
        def _target_model(alias):
            return alias.alias_model_id.model
        def _target_env(alias):
            return self.env[_target_model(alias)]

        # fetch impacted records, classify by model
        recs_by_model = defaultdict(list)
        for alias in tocheck:
            # owner record (like 'project.project' for aliases creating new 'project.task')
            if alias.alias_parent_model_id and alias.alias_parent_thread_id:
                if _owner_env(alias)._mail_get_company_field():
                    recs_by_model[_owner_model(alias)].append(alias.alias_parent_thread_id)
            # target record (like 'mail.group' updating a given group)
            if alias.alias_model_id and alias.alias_force_thread_id:
                if _target_env(alias)._mail_get_company_field():
                    recs_by_model[_target_model(alias)].append(alias.alias_force_thread_id)

        # helpers to fetch owner / target with prefetching
        def _fetch_owner(alias):
            if alias.alias_parent_thread_id in recs_by_model[alias.alias_parent_model_id.model]:
                return _owner_env(alias).with_prefetch(
                    recs_by_model[_owner_model(alias)]
                ).browse(alias.alias_parent_thread_id)
            return None
        def _fetch_target(alias):
            if alias.alias_force_thread_id in recs_by_model[alias.alias_model_id.model]:
                return _target_env(alias).with_prefetch(
                    recs_by_model[_target_model(alias)]
                ).browse(alias.alias_force_thread_id)
            return None

        # check company domains are compatible
        for alias in tocheck:
            if owner := _fetch_owner(alias):
                company = owner[owner._mail_get_company_field()]
                if company and company.alias_domain_id != alias.alias_domain_id and alias.alias_domain_id.company_ids:
                    raise ValidationError(_(
                        "We could not create alias %(alias_name)s because domain "
                        "%(alias_domain_name)s belongs to company %(alias_company_names)s "
                        "while the owner document belongs to company %(company_name)s.",
                        alias_company_names=','.join(alias.alias_domain_id.company_ids.mapped('name')),
                        alias_domain_name=alias.alias_domain_id.name,
                        alias_name=alias.display_name,
                        company_name=company.name,
                    ))
            if target := _fetch_target(alias):
                company = target[target._mail_get_company_field()]
                if company and company.alias_domain_id != alias.alias_domain_id and alias.alias_domain_id.company_ids:
                    raise ValidationError(_(
                        "We could not create alias %(alias_name)s because domain "
                        "%(alias_domain_name)s belongs to company %(alias_company_names)s "
                        "while the target document belongs to company %(company_name)s.",
                        alias_company_names=','.join(alias.alias_domain_id.company_ids.mapped('name')),
                        alias_domain_name=alias.alias_domain_id.name,
                        alias_name=alias.display_name,
                        company_name=company.name,
                    ))

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
    def _check_alias_domain_clash(self):
        """ Within a given alias domain, aliases should not conflict with bounce
        or catchall email addresses, as emails should be unique for the gateway. """
        failing = self.filtered(lambda alias: alias.alias_name and alias.alias_name in [
            alias.alias_domain_id.bounce_alias, alias.alias_domain_id.catchall_alias
        ])
        if failing:
            raise ValidationError(
                _('Aliases %(alias_names)s is already used as bounce or catchall address. Please choose another alias.',
                  alias_names=', '.join(failing.mapped('display_name')))
            )

    @api.depends('alias_domain_id.name', 'alias_name')
    def _compute_alias_full_name(self):
        """ A bit like display_name, but without the 'inactive alias' UI display.
        Moreover it is stored, allowing to search on it. """
        for record in self:
            if record.alias_domain_id and record.alias_name:
                record.alias_full_name = f"{record.alias_name}@{record.alias_domain_id.name}"
            elif record.alias_name:
                record.alias_full_name = record.alias_name
            else:
                record.alias_full_name = False

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

    @api.depends('alias_contact', 'alias_defaults', 'alias_model_id')
    def _compute_alias_status(self):
        """Reset alias_status to "not_tested" when fields, that can be the source of an error, are modified."""
        self.alias_status = 'not_tested'

    @api.model_create_multi
    def create(self, vals_list):
        """ Creates mail.alias records according to the values provided in
        ``vals`` but sanitize 'alias_name' by replacing certain unsafe
        characters; set default alias domain if not given.

        :raise UserError: if given (alias_name, alias_domain_id) already exists
          or if there are duplicates in given vals_list;
        """
        alias_names, alias_domains = [], []
        for vals in vals_list:
            vals['alias_name'] = self._sanitize_alias_name(vals.get('alias_name'))
            alias_names.append(vals['alias_name'])
            vals['alias_domain_id'] = vals.get('alias_domain_id', self.env.company.alias_domain_id.id)
            alias_domains.append(self.env['mail.alias.domain'].browse(vals['alias_domain_id']))

        self._check_unique(alias_names, alias_domains)
        return super().create(vals_list)

    def write(self, vals):
        """ Raise UserError with a meaningful message instead of letting the
        uniqueness constraint raise an SQL error. To check uniqueness we have
        to rebuild pairs of names / domains to validate, taking into account
        that a void alias_domain_id is acceptable (but also raises for
        uniqueness).
        """
        alias_names, alias_domains = [], []
        if 'alias_name' in vals:
            vals['alias_name'] = self._sanitize_alias_name(vals['alias_name'])
        if vals.get('alias_name') and self.ids:
            alias_names = [vals['alias_name']] * len(self)
        elif 'alias_name' not in vals and 'alias_domain_id' in vals:
            # avoid checking when writing the same value
            if [vals['alias_domain_id']] != self.alias_domain_id.ids:
                alias_names = self.filtered('alias_name').mapped('alias_name')

        if alias_names:
            tocheck_records = self if vals.get('alias_name') else self.filtered('alias_name')
            if 'alias_domain_id' in vals:
                alias_domains = [self.env['mail.alias.domain'].browse(vals['alias_domain_id'])] * len(tocheck_records)
            else:
                alias_domains = [record.alias_domain_id for record in tocheck_records]
            self._check_unique(alias_names, alias_domains)

        return super().write(vals)

    def _check_unique(self, alias_names, alias_domains):
        """ Check unicity constraint won't be raised, otherwise raise a UserError
        with a complete error message. Also check unicity against alias config
        parameters.

        :param list alias_names: a list of names (considered as sanitized
          and ready to be sent to DB);
        :param list alias_domains: list of alias_domain records under which
          the check is performed, as uniqueness is performed for given pair
          (name, alias_domain);
        """
        if len(alias_names) != len(alias_domains):
            msg = (f"Invalid call to '_check_unique': names and domains should make coherent lists, "
                   f"received {', '.join(alias_names)} and {', '.join(alias_domains.mapped('name'))}")
            raise ValueError(msg)

        # reorder per alias domain, keep only not void alias names (void domain also checks uniqueness)
        domain_to_names = defaultdict(list)
        for alias_name, alias_domain in zip(alias_names, alias_domains):
            if alias_name and alias_name in domain_to_names[alias_domain]:
                raise UserError(
                    _('Email aliases %(alias_name)s cannot be used on several records at the same time. Please update records one by one.',
                      alias_name=alias_name)
                )
            if alias_name:
                domain_to_names[alias_domain].append(alias_name)

        # matches existing alias
        domain = expression.OR([
            ['&', ('alias_name', 'in', alias_names), ('alias_domain_id', '=', alias_domain.id)]
            for alias_domain, alias_names in domain_to_names.items()
        ])
        if domain and self:
            domain = expression.AND([domain, [('id', 'not in', self.ids)]])
        existing = self.search(domain, limit=1) if domain else self.env['mail.alias']
        if not existing:
            return
        if existing.alias_parent_model_id and existing.alias_parent_thread_id:
            parent_name = self.env[existing.alias_parent_model_id.model].sudo().browse(existing.alias_parent_thread_id).display_name
            msg_begin = _(
                'Alias %(matching_name)s (%(current_id)s) is already linked with %(alias_model_name)s (%(matching_id)s) and used by the %(parent_name)s %(parent_model_name)s.',
                alias_model_name=existing.alias_model_id.name,
                current_id=self.ids if self else _('your alias'),
                matching_id=existing.id,
                matching_name=existing.display_name,
                parent_name=parent_name,
                parent_model_name=existing.alias_parent_model_id.name
            )
        else:
            msg_begin = _(
                'Alias %(matching_name)s (%(current_id)s) is already linked with %(alias_model_name)s (%(matching_id)s).',
                alias_model_name=existing.alias_model_id.name,
                current_id=self.ids if self else _('new'),
                matching_id=existing.id,
                matching_name=existing.display_name,
            )
        msg_end = _('Choose another value or change it on the other document.')
        raise UserError(f'{msg_begin} {msg_end}')

    @api.model
    def _sanitize_allowed_domains(self, allowed_domains):
        """ When having aliases checked on email left-part only we may define
        an allowed list for right-part filtering, allowing more fine-grain than
        either alias domain, either everything. This method sanitized its value. """
        value = [domain.strip().lower() for domain in allowed_domains.split(',') if domain.strip()]
        if not value:
            raise ValidationError(_(
                "Value %(allowed_domains)s for `mail.catchall.domain.allowed` cannot be validated.\n"
                "It should be a comma separated list of domains e.g. example.com,example.org.",
                allowed_domains=allowed_domains
            ))
        return ",".join(value)

    @api.model
    def _sanitize_alias_name(self, name, is_email=False):
        """ Cleans and sanitizes the alias name. In some cases we want the alias
        to be a complete email instead of just a left-part (when sanitizing
        default.from for example). In that case we extract the right part and
        put it back after sanitizing the left part.

        :param str name: the alias name to sanitize;
        :param bool is_email: whether to keep a right part, otherwise only
          left part is kept;

        :return str: sanitized alias name
        """
        sanitized_name = name.strip() if name else ''
        if is_email:
            right_part = sanitized_name.lower().partition('@')[2]
        else:
            right_part = False
        if sanitized_name:
            sanitized_name = remove_accents(sanitized_name).lower().split('@')[0]
            # cannot start and end with dot
            sanitized_name = re.sub(r'^\.+|\.+$|\.+(?=\.)', '', sanitized_name)
            # subset of allowed characters
            sanitized_name = re.sub(r'[^\w!#$%&\'*+\-/=?^_`{|}~.]+', '-', sanitized_name)
            sanitized_name = sanitized_name.encode('ascii', errors='replace').decode()
        if not sanitized_name.strip():
            return False
        return f'{sanitized_name}@{right_part}' if is_email and right_part else sanitized_name

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
