# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.fields import Domain


class MailingContact(models.Model):
    """Model of a contact. This model is different from the partner model
    because it holds only some basic information: name, email. The purpose is to
    be able to deal with large contact list to email without bloating the partner
    base."""
    _name = 'mailing.contact'
    _inherit = ['mail.thread.blacklist', 'properties.base.definition.mixin']
    _description = 'Mailing Contact'
    _order = 'name ASC, id DESC'
    _mailing_enabled = True

    @api.model
    def default_get(self, fields):
        """ When coming from a mailing list we may have a default_list_ids context
        key. We should use it to create subscription_ids default value that
        are displayed to the user as list_ids is not displayed on form view. """
        res = super().default_get(fields)
        if 'subscription_ids' in fields and not res.get('subscription_ids'):
            list_ids = self.env.context.get('default_list_ids')
            if 'default_list_ids' not in res and list_ids and isinstance(list_ids, (list, tuple)):
                res['subscription_ids'] = [
                    (0, 0, {'list_id': list_id}) for list_id in list_ids]
        return res

    name = fields.Char('Name', compute='_compute_name', readonly=False, store=True, tracking=True)
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    company_name = fields.Char(string='Company Name')
    email = fields.Char('Email')
    list_ids = fields.Many2many(
        'mailing.list', 'mailing_subscription',
        'contact_id', 'list_id', string='Mailing Lists')
    subscription_ids = fields.One2many(
        'mailing.subscription', 'contact_id', string='Subscription Information')
    country_id = fields.Many2one('res.country', string='Country')
    tag_ids = fields.Many2many('res.partner.category', string='Tags')
    opt_out = fields.Boolean(
        'Opt Out',
        compute='_compute_opt_out', search='_search_opt_out',
        help='Opt out flag for a specific mailing list. '
             'This field should not be used in a view without a unique and active mailing list context.')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """ Hide first and last name field if the split name feature is not enabled. """
        res = super().fields_get(allfields, attributes)
        if not self._is_name_split_activated():
            if 'first_name' in res:
                res['first_name']['searchable'] = False
            if 'last_name' in res:
                res['last_name']['searchable'] = False
        return res

    @api.model
    def _search_opt_out(self, operator, value):
        if operator != 'in':
            return NotImplemented

        if 'default_list_ids' in self.env.context and isinstance(self.env.context['default_list_ids'], (list, tuple)) and len(self.env.context['default_list_ids']) == 1:
            [active_list_id] = self.env.context['default_list_ids']
            subscriptions = self.env['mailing.subscription']._search([
                ('list_id', '=', active_list_id),
                ('opt_out', '=', True),
            ])
            return [('id', 'in', subscriptions.subselect('contact_id'))]
        return Domain.FALSE

    @api.depends('first_name', 'last_name')
    def _compute_name(self):
        for record in self:
            if record.first_name or record.last_name:
                record.name = ' '.join(name_part for name_part in (record.first_name, record.last_name) if name_part)

    @api.depends('subscription_ids')
    @api.depends_context('default_list_ids')
    def _compute_opt_out(self):
        if 'default_list_ids' in self.env.context and isinstance(self.env.context['default_list_ids'], (list, tuple)) and len(self.env.context['default_list_ids']) == 1:
            [active_list_id] = self.env.context['default_list_ids']
            for record in self:
                active_subscription_list = record.subscription_ids.filtered(lambda l: l.list_id.id == active_list_id)
                record.opt_out = active_subscription_list.opt_out
        else:
            for record in self:
                record.opt_out = False

    @api.model_create_multi
    def create(self, vals_list):
        """ Synchronize default_list_ids (currently used notably for computed
        fields) default key with subscription_ids given by user when creating
        contacts.

        Those two values have the same purpose, adding a list to to the contact
        either through a direct write on m2m, either through a write on middle
        model subscription.

        This is a bit hackish but is due to default_list_ids key being
        used to compute oupt_out field. This should be cleaned in master but here
        we simply try to limit issues while keeping current behavior. """
        default_list_ids = self.env.context.get('default_list_ids')
        default_list_ids = default_list_ids if isinstance(default_list_ids, (list, tuple)) else []

        for vals in vals_list:
            if vals.get('list_ids') and vals.get('subscription_ids'):
                raise UserError(_('You should give either list_ids, either subscription_ids to create new contacts.'))

        if default_list_ids:
            for vals in vals_list:
                if vals.get('list_ids'):
                    continue
                current_list_ids = []
                subscription_ids = vals.get('subscription_ids') or []
                for subscription in subscription_ids:
                    if len(subscription) == 3:
                        current_list_ids.append(subscription[2]['list_id'])
                for list_id in set(default_list_ids) - set(current_list_ids):
                    subscription_ids.append((0, 0, {'list_id': list_id}))
                vals['subscription_ids'] = subscription_ids

        records = super(MailingContact, self.with_context(default_list_ids=False)).create(vals_list)

        # We need to invalidate list_ids or subscription_ids because list_ids is a many2many
        # using a real model as table ('mailing.subscription') and the ORM doesn't automatically
        # update/invalidate the `list_ids`/`subscription_ids` cache correctly.
        for record in records:
            if record.list_ids:
                record.invalidate_recordset(['subscription_ids'])
            elif record.subscription_ids:
                record.invalidate_recordset(['list_ids'])
        return records

    def copy(self, default=None):
        """ Cleans the default_list_ids while duplicating mailing contact in context of
        a mailing list because we already have subscription lists copied over for newly
        created contact, no need to add the ones from default_list_ids again """
        if self.env.context.get('default_list_ids'):
            self = self.with_context(default_list_ids=False)
        return super().copy(default)

    @api.model
    def name_create(self, name):
        name, email = tools.parse_contact_from_email(name)
        contact = self.create({'name': name, 'email': email})
        return contact.id, contact.display_name

    @api.model
    def add_to_list(self, name, list_id):
        name, email = tools.parse_contact_from_email(name)
        contact = self.create({'name': name, 'email': email, 'list_ids': [(4, list_id)]})
        return contact.id, contact.display_name

    def action_import(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mass_mailing.mailing_contact_import_action")
        context = self.env.context.copy()
        action['context'] = context
        if (not context.get('default_mailing_list_ids') and context.get('from_mailing_list_ids')):
            action['context'].update({
                'default_mailing_list_ids': context.get('from_mailing_list_ids'),
            })

        return action

    def action_add_to_mailing_list(self):
        ctx = dict(self.env.context, default_contact_ids=self.ids)
        action = self.env["ir.actions.actions"]._for_xml_id("mass_mailing.mailing_contact_to_list_action")
        action['view_mode'] = 'form'
        action['target'] = 'new'
        action['context'] = ctx

        return action

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Mailing List Contacts'),
            'template': '/mass_mailing/static/xls/mailing_contact.xls'
        }]

    @api.model
    def _is_name_split_activated(self):
        """ Return whether the contact names are populated as first and last name or as a single field (name). """
        view = self.env.ref("mass_mailing.mailing_contact_view_tree_split_name", raise_if_not_found=False)
        return view and view.sudo().active
