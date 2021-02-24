# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import remove_accents, is_html_empty

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

    def _default_alias_domain(self):
        return self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")

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
    alias_domain = fields.Char('Alias domain', compute='_compute_alias_domain', default=_default_alias_domain)
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
        if any(alias.alias_name and not dot_atom_text.match(alias.alias_name) for alias in self):
            raise ValidationError(_("You cannot use anything else than unaccented latin characters in the alias address."))

    def _compute_alias_domain(self):
        alias_domain = self._default_alias_domain()
        for record in self:
            record.alias_domain = alias_domain

    @api.constrains('alias_defaults')
    def _check_alias_defaults(self):
        for alias in self:
            try:
                dict(ast.literal_eval(alias.alias_defaults))
            except Exception:
                raise ValidationError(_('Invalid expression, it must be a literal python dictionary definition e.g. "{\'field\': \'value\'}"'))

    @api.model
    def create(self, vals):
        """ Creates an email.alias record according to the values provided in ``vals``,
            with 2 alterations: the ``alias_name`` value may be cleaned  by replacing
            certain unsafe characters, and the ``alias_model_id`` value will set to the
            model ID of the ``model_name`` context value, if provided. Also, it raises
            UserError if given alias name is already assigned.
        """
        if vals.get('alias_name'):
            vals['alias_name'] = self._clean_and_check_unique(vals.get('alias_name'))
        return super(Alias, self).create(vals)

    def write(self, vals):
        """"Raises UserError if given alias name is already assigned"""
        if vals.get('alias_name') and self.ids:
            vals['alias_name'] = self._clean_and_check_unique(vals.get('alias_name'))
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

    def _clean_and_check_unique(self, name):
        """When an alias name appears to already be an email, we keep the local
        part only. A sanitizing / cleaning is also performed on the name. If
        name already exists an UserError is raised. """
        sanitized_name = remove_accents(name).lower().split('@')[0]
        sanitized_name = re.sub(r'[^\w+.]+', '-', sanitized_name)
        sanitized_name = sanitized_name.encode('ascii', errors='replace').decode()

        catchall_alias = self.env['ir.config_parameter'].sudo().get_param('mail.catchall.alias')
        bounce_alias = self.env['ir.config_parameter'].sudo().get_param('mail.bounce.alias')
        domain = [('alias_name', '=', sanitized_name)]
        if self:
            domain += [('id', 'not in', self.ids)]
        if sanitized_name in [catchall_alias, bounce_alias] or self.search_count(domain):
            raise UserError(_('The e-mail alias is already used. Please enter another one.'))
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
        return _("""Hi,<br/>
The following email sent to %s cannot be accepted because this is a private email address.
Only allowed people can contact us at this address.""", self.display_name)

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
        template = self.env.ref('mail.mail_bounce_alias_security', raise_if_not_found=True)
        return template._render({
            'body': body,
            'message': message_dict
        }, engine='ir.qweb', minimal_qcontext=True)
