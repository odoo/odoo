# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import remove_accents, is_html_empty

_logger = logging.getLogger(__name__)


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
    alias_domain = fields.Char('Alias domain', compute='_get_alias_domain',
                               default=lambda self: self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain"))
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

    def _get_alias_domain(self):
        alias_domain = self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")
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
        model_name = self._context.get('alias_model_name')
        parent_model_name = self._context.get('alias_parent_model_name')
        if vals.get('alias_name'):
            vals['alias_name'] = self._clean_and_check_unique(vals.get('alias_name'))
        if model_name:
            model = self.env['ir.model']._get(model_name)
            vals['alias_model_id'] = model.id
        if parent_model_name:
            model = self.env['ir.model']._get(parent_model_name)
            vals['alias_parent_model_id'] = model.id
        return super(Alias, self).create(vals)

    def write(self, vals):
        """"Raises UserError if given alias name is already assigned"""
        if vals.get('alias_name') and self.ids:
            vals['alias_name'] = self._clean_and_check_unique(vals.get('alias_name'), alias_ids=self.ids)
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

    @api.model
    def _clean_and_check_unique(self, name, alias_ids=False):
        """When an alias name appears to already be an email, we keep the local part only.
           Also, if ``name`` is already taken, it raises UserError.
        """
        name = remove_accents(name).lower().split('@')[0]
        name = re.sub(r'[^\w+.]+', '-', name)
        ICP = self.env['ir.config_parameter'].sudo()
        catchall_alias = ICP.get_param('mail.catchall.alias')
        bounce_alias = ICP.get_param('mail.bounce.alias')
        domain = [('alias_name', '=', name)]
        if alias_ids:
            domain += [('id', 'not in', alias_ids)]
        if name in [catchall_alias, bounce_alias] or self.search(domain):
            raise UserError(_('The e-mail alias is already used. Please enter another one.'))
        return name

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
Only allowed people can contact us at this address.""" % message_dict.get('to'))

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
        return template.render({
            'body': body,
            'message': message_dict
        }, engine='ir.qweb', minimal_qcontext=True)


class AliasMixin(models.AbstractModel):
    """ A mixin for models that inherits mail.alias. This mixin initializes the
        alias_id column in database, and manages the expected one-to-one
        relation between your model and mail aliases.
    """
    _name = 'mail.alias.mixin'
    _inherits = {'mail.alias': 'alias_id'}
    _description = 'Email Aliases Mixin'

    alias_id = fields.Many2one('mail.alias', string='Alias', ondelete="restrict", required=True)

    def get_alias_model_name(self, vals):
        """ Return the model name for the alias. Incoming emails that are not
            replies to existing records will cause the creation of a new record
            of this alias model. The value may depend on ``vals``, the dict of
            values passed to ``create`` when a record of this model is created.
        """
        return None

    def get_alias_values(self):
        """ Return values to create an alias, or to write on the alias after its
            creation.
        """
        return {'alias_parent_thread_id': self.id}

    @api.model
    def create(self, vals):
        """ Create a record with ``vals``, and create a corresponding alias. """
        record = super(AliasMixin, self.with_context(
            alias_model_name=self.get_alias_model_name(vals),
            alias_parent_model_name=self._name,
        )).create(vals)
        record.alias_id.sudo().write(record.get_alias_values())
        return record

    def unlink(self):
        """ Delete the given records, and cascade-delete their corresponding alias. """
        aliases = self.mapped('alias_id')
        res = super(AliasMixin, self).unlink()
        aliases.unlink()
        return res

    def _init_column(self, name):
        """ Create aliases for existing rows. """
        super(AliasMixin, self)._init_column(name)
        if name != 'alias_id':
            return

        # both self and the alias model must be present in 'ir.model'
        IM = self.env['ir.model']
        IM._reflect_model(self)
        IM._reflect_model(self.env[self.get_alias_model_name({})])

        alias_ctx = {
            'alias_model_name': self.get_alias_model_name({}),
            'alias_parent_model_name': self._name,
        }
        alias_model = self.env['mail.alias'].sudo().with_context(alias_ctx).browse([])

        child_ctx = {
            'active_test': False,       # retrieve all records
            'prefetch_fields': False,   # do not prefetch fields on records
        }
        child_model = self.sudo().with_context(child_ctx).browse([])

        for record in child_model.search([('alias_id', '=', False)]):
            # create the alias, and link it to the current record
            alias = alias_model.create(record.get_alias_values())
            record.with_context(mail_notrack=True).alias_id = alias
            _logger.info('Mail alias created for %s %s (id %s)',
                         record._name, record.display_name, record.id)

    def _alias_check_contact(self, message, message_dict, alias):
        """ Main mixin method that inheriting models may inherit in order
        to implement a specifc behavior. """
        return self._alias_check_contact_on_record(self, message, message_dict, alias)

    def _alias_check_contact_on_record(self, record, message, message_dict, alias):
        """ Generic method that takes a record not necessarily inheriting from
        mail.alias.mixin. """
        author = self.env['res.partner'].browse(message_dict.get('author_id', False))
        if alias.alias_contact == 'followers':
            if not record.ids:
                return _('incorrectly configured alias (unknown reference record)')
            if not hasattr(record, "message_partner_ids") or not hasattr(record, "message_channel_ids"):
                return _('incorrectly configured alias')
            accepted_partner_ids = record.message_partner_ids | record.message_channel_ids.mapped('channel_partner_ids')
            if not author or author not in accepted_partner_ids:
                return _('restricted to followers')
        elif alias.alias_contact == 'partners' and not author:
            return _('restricted to known authors')
        return True
