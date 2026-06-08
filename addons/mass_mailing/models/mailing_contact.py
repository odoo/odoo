# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from collections import defaultdict
from itertools import product

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import clean_context
from odoo.tools.float_utils import float_round

MAX_FROM_PARTNERS = 500


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
    mailing_count = fields.Integer('Number of Mailing', compute='_compute_statistics')
    received_ratio = fields.Float('Received Ratio', compute='_compute_statistics')
    opened_ratio = fields.Float('Opened Ratio', compute='_compute_statistics')
    replied_ratio = fields.Float('Replied Ratio', compute='_compute_statistics')
    clicks_ratio = fields.Float('Clicks Ratio', compute="_compute_clicks_ratio")
    # Datetimes that mirror the onces in mailing_trace for the corresponding contact.
    # They get updated from the mailing.trace model.
    last_opened_datetime = fields.Datetime('Last Opened On')
    last_clicked_datetime = fields.Datetime('Last Clicked On')
    last_replied_datetime = fields.Datetime('Last Replied On')

    partner_id = fields.Many2one('res.partner', string='Contact', index='btree_not_null')

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
        if active_list_id := self._get_context_active_list_id():
            for record in self:
                active_subscription_list = record.subscription_ids.filtered(lambda l: l.list_id.id == active_list_id)
                record.opt_out = active_subscription_list.opt_out
        else:
            for record in self:
                record.opt_out = False

    @api.model
    def _get_context_active_list_id(self):
        if (
            'default_list_ids' in self.env.context
            and isinstance(self.env.context['default_list_ids'], (list, tuple))
            and len(self.env.context['default_list_ids']) == 1
        ):
            return self.env.context['default_list_ids'][0]
        return None

    def _compute_clicks_ratio(self):
        grouped_traces = dict(self.env['mailing.trace'].sudo()._read_group(
            domain=[('model', '=', 'mailing.contact'), ('res_id', 'in', self.ids)],
            groupby=[('res_id')],
            aggregates=[('id:count_distinct')]
        ))
        grouped_clicks = dict(self.env['link.tracker.click'].sudo()._read_group(
            domain=[('mailing_trace_id.model', '=', 'mailing.contact'), ('mailing_trace_id.res_id', 'in', self.ids)],
            groupby=[('mailing_trace_id.res_id')],
            aggregates=[('mailing_trace_id:count_distinct')]
        ))
        for contact in self:
            contact.clicks_ratio = float_round(100 * grouped_clicks.get(contact.id, 0) / grouped_traces.get(contact.id, 1), precision_digits=2)

    def _compute_statistics(self):
        """ Compute the mailing statistics for the mailing contact """
        result = self.env["mailing.trace"].sudo()._read_group(
            [('model', '=', 'mailing.contact'), ('res_id', 'in', self.ids)],
            ['res_id', 'trace_status'],
            ['__count'])

        result_per_contact = defaultdict(lambda: defaultdict(int))
        for res_id, trace_status, count in result:
            result_per_contact[res_id][trace_status] = count

        for contact in self:
            line = result_per_contact[contact.id]
            expected = sum(line.values())
            delivered = line['sent'] + line['open'] + line['reply']
            opened = line['open'] + line['reply']
            failed = line['error'] + line['bounce']
            total = (expected - line['cancel']) or 1
            total_no_error = (expected - line['cancel'] - failed) or 1
            contact.mailing_count = delivered
            contact.received_ratio = float_round(100.0 * delivered / total, precision_digits=2)
            contact.opened_ratio = float_round(100.0 * opened / total_no_error, precision_digits=2)
            contact.replied_ratio = float_round(100.0 * line['reply'] / total_no_error, precision_digits=2)

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
        action['context'] = ctx | json.loads(action['context'])

        return action

    def action_open_base_import(self):
        """Open the base import wizard to import mailing contacts with a xlsx file."""

        return {
            'type': 'ir.actions.client',
            'tag': 'import',
            'name': _('Import Mailing Contacts'),
            'params': {
                'context': self.env.context,
                'active_model': 'mailing.contact',
            },
        }

    def action_view_mailings(self):
        action = self.env["ir.actions.actions"]._for_xml_id('mass_mailing.mailing_mailing_action_mail')
        traces_grouped = dict(self.env['mailing.trace']._read_group(
            [('model', '=', 'mailing.contact'), ('res_id', 'in', self.ids), ('sent_datetime', '!=', False)],
            ['mass_mailing_id'],
            ['__count']
        ))
        mailing_ids = [m.id for m in traces_grouped]
        action['domain'] = [('id', 'in', mailing_ids)]
        return action

    def action_view_received(self):
        domain = Domain.AND([Domain('model', '=', 'mailing.contact'), Domain('res_id', 'in', self.ids)])
        return self.env['mailing.trace'].with_context({'search_default_filter_delivered': 1, 'search_default_group_sent_date': 1})._action_view_mailing_statistics_filtered(domain, 'delivered')

    def action_view_opened(self):
        domain = Domain.AND([Domain('model', '=', 'mailing.contact'), Domain('res_id', 'in', self.ids)])
        return self.env['mailing.trace'].with_context({'search_default_filter_opened': 1})._action_view_mailing_statistics_filtered(domain, 'open')

    def action_view_replied(self):
        domain = Domain.AND([Domain('model', '=', 'mailing.contact'), Domain('res_id', 'in', self.ids)])
        return self.env['mailing.trace'].with_context({'search_default_filter_replied': 1})._action_view_mailing_statistics_filtered(domain, 'reply')

    def action_view_clicked(self):
        domain = [('mailing_trace_id.model', '=', 'mailing.contact'), ('mailing_trace_id.res_id', 'in', self.ids)]
        return self.env['link.tracker.click']._action_view_mailing_statistics(domain)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Template for Mailing Contacts'),
            'template': '/mass_mailing/static/xls/mailing_contact.xls'
        }]

    @api.model
    def _is_name_split_activated(self):
        """ Return whether the contact names are populated as first and last name or as a single field (name). """
        view = self.env.ref("mass_mailing.mailing_contact_view_tree_split_name", raise_if_not_found=False)
        return view and view.sudo().active

    def _creation_message(self):
        self.ensure_one()
        mailing_contact_source = self.env.context.get('mailing_contact_source')
        if mailing_contact_source != 'partner':
            return super()._creation_message()
        return self.env._(
            "%(record_name)s created from %(link)s",
            record_name=self.env['ir.model']._get(self._name).name,
            link=self.partner_id._get_html_link()
        )

    @api.model
    def _from_partners(self, partners):
        """Return Mailing Contacts and count of `partners` without contact details.

        Return (existing or new) mailing contacts for the given partners in
        the given mailing list context, linking unlinked contacts to their partner.
        Partners with no contact details are excluded and counted in the second
        return value.

        Matches require at least one key field in common and no conflicts.
        See `_from_partners_get_match_unique_field_names`.
        Records are not matched when:
         * they only have a common name (no email or extension-provided
           criterion)
         * a partner and a contacts have a matching field mismatch:
           e.g., same email but different phone when mass mailing SMS is installed

        To prevent data explosion, a duplicates management strategy is implemented:
         * When multiple *input* partners have the same matching criteria,
           the same contact is returned for those and is linked to the most recently
           created partner.
         * When multiple mailing contacts share the same email, the best match
           based on subscription confidence is returned; See `_get_sort_key`.
           Contacts among them without partner_id are all linked to the partner.
         * If the best-matching contact is already linked to a different partner,
           it is returned as-is; no merge is performed as we consider it is the
           prerogative of the users to manage their records as they see fit,
           including if and how to merge duplicates.

        :returns: tuple of (matched/created contacts recordset, number of partners
           skipped due to missing contact details)
        """
        active_list_id = self._get_context_active_list_id()
        if active_list_id:
            # Apply active list context for _compute_mailing_contact_id used to efficiently
            # identify already linked relevant contacts.
            partners = partners.with_context(default_list_ids=[active_list_id])

        # Order partners for whom to find a contact by id desc to link found/created contacts
        # with that partner even if it is returned for other partners too.
        partners_to_match = partners.filtered(lambda p: not p.mailing_contact_id).sorted('id desc')
        if len(partners_to_match) > MAX_FROM_PARTNERS:
            msg = self.env._("Oops! You can't add more than %(count)s contacts to a Mailing List at once.\n"
                             "Please reduce your selection and try again.", count=MAX_FROM_PARTNERS)
            raise UserError(msg)

        contacts = partners.mailing_contact_id

        match_fields = self._from_partners_get_match_unique_field_names()
        partners_per_key = partners_to_match.grouped(lambda p: tuple(p[field_name] for field_name in match_fields))
        partners_for_creation = self.env['res.partner']
        partners_without_details = partners_per_key.pop(tuple(False for _ in match_fields), self.env['res.partner'])
        partners_to_match -= partners_without_details
        existing_contacts = self.search_fetch(Domain.OR(
            Domain(field_name, 'in', {v for v in partners_to_match.mapped(field_name) if v})
            for field_name in match_fields
        ), ['partner_id', *match_fields])

        def _matching_keys(contact_or_partner):
            """Generate all non-all-false combinations of matching values for contact_or_partner.

            E.g., with "email" and "phone": [(email_1, phone_1), (email_1, False), (False, phone_1)].
            This is used to match partners and contact efficiently looking up keys in maps after a single iteration.
            """
            field_values_or_false = ({contact_or_partner[field_name], False} for field_name in match_fields)
            return [k for k in product(*field_values_or_false) if any(k)]

        existing_contacts_per_key = defaultdict(self.browse)
        for contact in existing_contacts:
            for key in _matching_keys(contact):
                existing_contacts_per_key[key] |= contact

        for key, partners_to_match in partners_per_key.items():
            latest_partner = partners_to_match[0]
            partner_keys = _matching_keys(latest_partner)
            keys_contacts = self.browse().concat(
                contact for key in partner_keys for contact in existing_contacts_per_key[key])
            matching_contacts = keys_contacts.filtered(lambda c: c._is_partner_compatible(latest_partner))
            if not matching_contacts:
                partners_for_creation |= latest_partner
                continue
            if len(matching_contacts) > 1:
                best_contact = matching_contacts.sorted(lambda c: c._get_sort_key(list_id=active_list_id))[-1]
            else:
                best_contact = matching_contacts
            for matching_contact in matching_contacts:
                if not matching_contact.partner_id:
                    matching_contact.partner_id = latest_partner

            contacts |= best_contact

        if partners_for_creation:
            vals_list = [self._from_partners_get_create_vals(partner) for partner in partners_for_creation]
            create_context = clean_context(self.env.context) | {'mailing_contact_source': 'partner'}
            new_contacts = self.with_context(create_context).create(vals_list)
            contacts |= new_contacts

        return contacts, len(partners_without_details)

    @api.model
    def _from_partners_get_create_vals(self, partner):
        return {
            'company_name': partner.parent_id.name,
            'country_id': partner.country_id.id or partner.parent_id.country_id.id,
            'email': partner.email,
            'email_normalized': partner.email_normalized,
            'name': partner.name,
            'partner_id': partner.id,
            'tag_ids': partner.category_id,
        }

    @api.model
    def _from_partners_get_match_unique_field_names(self):
        return ['email_normalized']

    def _get_sort_key(self, list_id=None, partner=None):
        """Return contact sorting key for preferred matching ordering.

        Priority is given as:
          1. (top) opted out of list_id (if provided)
          2. Subscribed to list_id (if provided)
          3. Highest active subscriptions count
          4. Number of contact fields in common with `partner` (if provided, lowest if any field conflict).
          5. id
        :param int|None list_id: mailing list id to check subscription and opt-out.
        :param models.Model partner: Partner to compare self with.
        :rtype: tuple[int]
        """
        self.ensure_one()
        is_on_active_list = is_opted_out_on_active_list = False
        active_subscription_count = 0
        for subscription in self.subscription_ids:
            active_subscription_count += not subscription.opt_out
            if list_id and subscription.list_id.id == list_id:
                is_on_active_list = True
                is_opted_out_on_active_list |= subscription.opt_out
        nb_matches = self._is_partner_compatible(partner=partner)
        return is_opted_out_on_active_list, is_on_active_list, active_subscription_count, nb_matches, self.id

    def _is_partner_compatible(self, partner, match_fields=None):
        """Return the number of match_fields in common with partner, or 0 if any difference or no partner."""
        self.ensure_one()
        if not partner:
            return 0
        match_fields = match_fields or self._from_partners_get_match_unique_field_names()
        if set_on_both := tuple((self[f], partner[f]) for f in match_fields if self[f] and partner[f]):
            if all(contact_val == partner_val for contact_val, partner_val in set_on_both):
                return len(set_on_both)
        return 0
