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

    alias_name = fields.Char('Alias Name', copy=False, help="The name of the email alias, e.g. 'jobs' if you want to catch emails for <jobs@example.odoo.com>")
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
    alias_domain = fields.Char('Alias domain', compute='_compute_alias_domain')
    alias_parent_model_id = fields.Many2one(
        'ir.model', 'Parent Model',
        help="Parent model holding the alias. The model holding the alias reference "
             "is not necessarily the model given by alias_model_id "
             "(example: project (parent_model) and task (model))")
    alias_parent_thread_id = fields.Integer('Parent Record Thread ID', help="ID of the parent record holding the alias (example: project holding the task creation alias)")
    alias_contact = fields.Selection([
        ('everyone', 'Everyone'),
        ('partners', 'Authenticated Partners'),
        ('followers', 'Followers only')], default='everyone',
        string='Alias Contact Security', required=True,
        help="Policy to post a message on the document using the mailgateway.\n"
             "- everyone: everyone can post\n"
             "- partners: only authenticated partners\n"
             "- followers: only followers of the related document or members of following channels\n")
    alias_bounced_content = fields.Html(
        "Custom Bounced Message", translate=True,
        help="If set, this content will automatically be sent out to unauthorized users instead of the default message.")

    _sql_constraints = [
        ('alias_unique', 'UNIQUE(alias_name)', 'Unfortunately this email alias is already used, please choose a unique one')
    ]

    @api.constrains('alias_name')
    def _alias_is_ascii(self):
        """ The local-part ("display-name" <local-part@domain>) of an
            address only contains limited range of ascii characters.
            We DO NOT allow anything else than ASCII dot-atom formed
            local-part. Quoted-string and internationnal characters are
            to be rejected. See rfc5322 sections 3.4.1 and 3.2.3
        """
        for alias in self:
            if alias.alias_name and not dot_atom_text.match(alias.alias_name):
                raise ValidationError(_(
                    "You cannot use anything else than unaccented latin characters in the alias address (%s).",
                    alias.alias_name,
                ))

    @api.depends('alias_name')
    def _compute_alias_domain(self):
        self.alias_domain = self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")

    @api.constrains('alias_defaults')
    def _check_alias_defaults(self):
        for alias in self:
            try:
                dict(ast.literal_eval(alias.alias_defaults))
            except Exception:
                raise ValidationError(_('Invalid expression, it must be a literal python dictionary definition e.g. "{\'field\': \'value\'}"'))

    @api.model_create_multi
    def create(self, vals_list):
        """ Creates email.alias records according to the values provided in
        ``vals`` with 1 alteration:

          * ``alias_name`` value may be cleaned by replacing certain unsafe
            characters;

        :raise UserError: if given alias_name is already assigned or there are
        duplicates in given vals_list;
        """
        alias_names = [vals['alias_name'] for vals in vals_list if vals.get('alias_name')]
        if alias_names:
            sanitized_names = self._clean_and_check_unique(alias_names)
            for vals in vals_list:
                if vals.get('alias_name'):
                    vals['alias_name'] = sanitized_names[alias_names.index(vals['alias_name'])]
        return super(Alias, self).create(vals_list)

    def write(self, vals):
        """"Raises UserError if given alias name is already assigned"""
        if vals.get('alias_name') and self.ids:
            if len(self) > 1:
                raise UserError(_(
                    'Email alias %(alias_name)s cannot be used on %(count)d records at the same time. Please update records one by one.',
                    alias_name=vals['alias_name'], count=len(self)
                    ))
            vals['alias_name'] = self._clean_and_check_unique([vals.get('alias_name')])[0]
        return super(Alias, self).write(vals)

    def name_get(self):
        """Return the mail alias display alias_name, including the implicit
           mail catchall domain if exists from config otherwise "New Alias".
           e.g. `jobs@mail.odoo.com` or `jobs` or 'New Alias'
        """
        res = []
        for record in self:
            if record.alias_name and record.alias_domain:
                res.append((record['id'], "%s@%s" % (record.alias_name, record.alias_domain)))
            elif record.alias_name:
                res.append((record['id'], "%s" % (record.alias_name)))
            else:
                res.append((record['id'], _("Inactive Alias")))
        return res

    def _clean_and_check_unique(self, names):
        """When an alias name appears to already be an email, we keep the local
        part only. A sanitizing / cleaning is also performed on the name. If
        name already exists an UserError is raised. """

        def _sanitize_alias_name(name):
            """ Cleans and sanitizes the alias name """
            sanitized_name = remove_accents(name).lower().split('@')[0]
            sanitized_name = re.sub(r'[^\w+.]+', '-', sanitized_name)
            sanitized_name = re.sub(r'^\.+|\.+$|\.+(?=\.)', '', sanitized_name)
            sanitized_name = sanitized_name.encode('ascii', errors='replace').decode()
            return sanitized_name

        sanitized_names = [_sanitize_alias_name(name) for name in names]

        catchall_alias = self.env['ir.config_parameter'].sudo().get_param('mail.catchall.alias')
        bounce_alias = self.env['ir.config_parameter'].sudo().get_param('mail.bounce.alias')
        alias_domain = self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")

        # matches catchall or bounce alias
        for sanitized_name in sanitized_names:
            if sanitized_name in [catchall_alias, bounce_alias]:
                matching_alias_name = '%s@%s' % (sanitized_name, alias_domain) if alias_domain else sanitized_name
                raise UserError(
                    _('The e-mail alias %(matching_alias_name)s is already used as %(alias_duplicate)s alias. Please choose another alias.',
                      matching_alias_name=matching_alias_name,
                      alias_duplicate=_('catchall') if sanitized_name == catchall_alias else _('bounce'))
                )

        # matches existing alias
        domain = [('alias_name', 'in', sanitized_names)]
        if self:
            domain += [('id', 'not in', self.ids)]
        matching_alias = self.search(domain, limit=1)
        if not matching_alias:
            return sanitized_names

        sanitized_alias_name = _sanitize_alias_name(matching_alias.alias_name)
        matching_alias_name = '%s@%s' % (sanitized_alias_name, alias_domain) if alias_domain else sanitized_alias_name
        if matching_alias.alias_parent_model_id and matching_alias.alias_parent_thread_id:
            # If parent model and parent thread ID both are set, display document name also in the warning
            document_name = self.env[matching_alias.alias_parent_model_id.model].sudo().browse(matching_alias.alias_parent_thread_id).display_name
            raise UserError(
                _('The e-mail alias %(matching_alias_name)s is already used by the %(document_name)s %(model_name)s. Choose another alias or change it on the other document.',
                  matching_alias_name=matching_alias_name,
                  document_name=document_name,
                  model_name=matching_alias.alias_parent_model_id.name)
                )
        raise UserError(
            _('The e-mail alias %(matching_alias_name)s is already linked with %(alias_model_name)s. Choose another alias or change it on the linked model.',
              matching_alias_name=matching_alias_name,
              alias_model_name=matching_alias.alias_model_id.name)
        )

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
        return Markup(
            _("""<p>Dear Sender,<br /><br />
The message below could not be accepted by the address %(alias_display_name)s.
Only %(contact_description)s are allowed to contact it.<br /><br />
Please make sure you are using the correct address or contact us at %(default_email)s instead.<br /><br />
Kind Regards,</p>"""
             )) % {
                 'alias_display_name': self.display_name,
                 'contact_description': contact_description,
                 'default_email': default_email,
             }

    def _get_alias_contact_description(self):
        if self.alias_contact == 'partners':
            return _('addresses linked to registered partners')
        return _('some specific addresses')

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
