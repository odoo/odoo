# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime
from lxml.builder import E
from markupsafe import Markup

from odoo import api, exceptions, models, tools, _
from odoo.addons.mail.tools.alias_error import AliasError
from odoo.tools import parse_contact_from_email
from odoo.tools.mail import email_normalize, email_split_and_format
from odoo.tools.sql import column_exists

from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG

import logging

_logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = 'base'
    _mail_defaults_to_email = False

    # ------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------

    def _valid_field_parameter(self, field, name):
        # allow tracking on abstract models; see also 'mail.thread'
        return (
            name == 'tracking' and self._abstract
            or super()._valid_field_parameter(field, name)
        )

    def with_user(self, user):
        """Override to ensure the guest context is removed as the target user in a with_user should
        never be considered as being the guest of the outside env."""
        return super().with_user(user).with_context(guest=None)

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    def unlink(self):
        # Override unlink to delete records activities through (res_model, res_id)
        record_ids = self.ids if (not self._abstract and not self._transient) else []
        result = super().unlink()
        if record_ids and (
            # during uninstallation of module mail, the search below will crash
            not self.env.context.get(MODULE_UNINSTALL_FLAG) or (
                column_exists(self.env.cr, 'mail_activity', 'res_model')
                and column_exists(self.env.cr, 'mail_activity', 'res_id')
            )
        ):
            self.env['mail.activity'].with_context(active_test=False).sudo().search(
                [('res_model', '=', self._name), ('res_id', 'in', record_ids)]
            ).unlink()
        return result

    # ------------------------------------------------------------
    # CHECK ACCESS
    # ------------------------------------------------------------

    def _mail_get_operation_for_mail_message_operation(self, message_operation):
        """ Give document permission based on mail.message check permission.
        This is used when no other checks already granted permission (e.g.
        being notified, being author, ...). """
        valid_operations = {'read', 'write', 'unlink', 'create'}
        if message_operation not in valid_operations:
            raise ValueError('Invalid message operation, should be a valid ORM operation type')
        mail_post_access = getattr(self, '_mail_post_access', 'write')
        if mail_post_access not in valid_operations:
            raise ValueError('Invalid _mail_post_access, should be a valid ORM operation type')

        if message_operation == 'read':
            check_access = 'read'
        elif message_operation == 'create':
            check_access = mail_post_access
        else:
            check_access = 'write'
        return dict.fromkeys(self, check_access)

    def _mail_group_by_operation_for_mail_message_operation(self, message_operation):
        """ Globally reverse result of '_mail_get_operation_for_mail_message_operation'
        aka return documents for a given access to check on them. """
        document_operations = self._mail_get_operation_for_mail_message_operation(message_operation)
        operation_documents = defaultdict(lambda: self.env[self._name])
        for record, record_operation in document_operations.items():
            operation_documents[record_operation] += record
        # force prefetch in a post-loop as recordset concatenation may lose it
        for operation, records in operation_documents.items():
            records = records.with_prefetch(self.ids)
        return operation_documents

    # ------------------------------------------------------------
    # FIELDS HELPERS
    # ------------------------------------------------------------

    def _mail_get_alias_domains(self, default_company=False):
        """ Return alias domain linked to each record in self. It is based
        on the company (record's company, environment company) and fallback
        on the first found alias domain if configuration is not correct.

        :param <res.company> default_company: default company in case records
          have no company (or no company field); defaults to env.company;

        :return: for each record ID in self, found <mail.alias.domain>
        """
        record_companies = self._mail_get_companies(default=(default_company or self.env.company))

        # prepare default alias domain, fetch only if necessary
        default_domain = (default_company or self.env.company).alias_domain_id
        all_companies = self.env['res.company'].browse({comp.id for comp in record_companies.values()})
        # early optimization: search only if necessary
        if not default_domain and any(not comp.alias_domain_id for comp in all_companies):
            default_domain = self.env['mail.alias.domain'].search([], limit=1)

        return {
            record.id: (
                record_companies[record.id].alias_domain_id or default_domain
            )
            for record in self
        }

    @api.model
    def _mail_get_company_field(self):
        return 'company_id' if 'company_id' in self else False

    def _mail_get_companies(self, default=False):
        """ Return company linked to each record in self.

        :param <res.company> default: default value if no company field is found
          or if it holds a void value. Defaults to a void recordset;

        :return: for each record ID in self, found <res.company>
        """
        default_company = default or self.env['res.company']
        company_fname = self._mail_get_company_field()
        return {
            record.id: (record[company_fname] or default_company) if company_fname else default_company
            for record in self
        }

    def _mail_get_customer(self, introspect_fields=False):
        """ Return the 'main partner' (customer business wise) of the record.
        Mainly a helper for future changes e.g. main customer in templates. """
        self.ensure_one()
        customers = self._mail_get_partners(introspect_fields=introspect_fields)[self.id]
        return customers[0] if customers else self.env['res.partner']

    @api.model
    def _mail_get_partner_fields(self, introspect_fields=False):
        """ This method returns the fields to use to find the contact to link
        when sending emails or notifications. Having partner is not always
        necessary but gives more flexibility to notifications management.

        :param bool introspect_fields: if no field is found by default
          heuristics, introspect model to find relational fields towards
          res.partner model. This is used notably when partners are
          mandatory like in voip;

        :return: list of valid field names that can be used to retrieve
          a partner (customer) on the record;
        """
        partner_fnames = [fname for fname in ('partner_id', 'partner_ids') if fname in self]
        if not partner_fnames and introspect_fields:
            partner_fnames = [
                fname for fname, fvalue in self._fields.items()
                if fvalue.type == 'many2one' and fvalue.comodel_name == 'res.partner'
            ]
        return partner_fnames

    def mail_get_partner_fields(self):
        return self._mail_get_partner_fields()

    def _mail_get_partners(self, introspect_fields=False):
        """ Give the default partners (customers) associated to customers.

        :param bool introspect_fields: see '_mail_get_partner_fields';

        :return: for each record ID, a res.partner recordsets being default
          customers to contact;
        """
        partner_fields = self._mail_get_partner_fields(introspect_fields=introspect_fields)
        all_pids = {pid for record in self for fn in partner_fields for pid in record[fn].ids}
        records_partners = {}
        for record in self:
            pids = tools.unique(pid for fn in partner_fields for pid in record[fn].ids)
            records_partners[record.id] = self.env['res.partner'].browse(pids).with_prefetch(all_pids)
        return records_partners

    @api.model
    def _mail_get_primary_email_field(self):
        """ Check if the "_primary_email" model attribute is correctly set and
        matches an existing field, and return it. Otherwise return None. """
        primary_email = getattr(self, '_primary_email', None)
        if primary_email and primary_email in self._fields:
            return primary_email
        return None

    def _mail_get_primary_email(self):
        """ Based on "_primary_email", fetch primary email. Helper to override
        when there is no easy field access. """
        primary_email = getattr(self, '_primary_email', None)
        fname = primary_email if primary_email and primary_email in self._fields else None
        return {
            record.id: record[fname] if fname else False for record in self
        }

    @api.model
    def mail_allowed_qweb_expressions(self):
        # QWeb expressions allowed if we are not template editor
        return (
            "object.name",
            "object.contact_name",
            "object.partner_id",
            "object.partner_id.name",
            "object.user_id",
            "object.user_id.name",
            "object.user_id.signature",
        )

    # ------------------------------------------------------------
    # GENERIC MAIL FEATURES
    # ------------------------------------------------------------

    def _mail_track(self, tracked_fields, initial_values):
        """ For a given record, fields to check (tuple column name, column info)
        and initial values, return a valid command to create tracking values.

        :param dict tracked_fields: fields_get of updated fields on which
          tracking is checked and performed;
        :param dict initial_values: dict of initial values for each updated
          fields;

        :return: a tuple (changes, tracking_value_ids) where
          changes: set of updated column names; contains onchange tracked fields
          that changed;
          tracking_value_ids: a list of ORM (0, 0, values) commands to create
          ``mail.tracking.value`` records;

        Override this method on a specific model to implement model-specific
        behavior. Also consider inheriting from ``mail.thread``. """
        self.ensure_one()
        updated = set()
        tracking_value_ids = []

        fields_track_info = self._mail_track_order_fields(tracked_fields)
        for col_name, _sequence in fields_track_info:
            if col_name not in initial_values:
                continue
            initial_value = initial_values[col_name]
            new_value = (
                # get the properties definition with the value
                # (not just the dict with the value)
                field.convert_to_read(self[col_name], self)
                if (field := self._fields[col_name]).type == 'properties'
                else self[col_name]
            )
            if new_value == initial_value or (not new_value and not initial_value):  # because browse null != False
                continue

            if self._fields[col_name].type == "properties":
                definition_record_field = self._fields[col_name].definition_record
                if self[definition_record_field] == initial_values[definition_record_field]:
                    # track the change only if the parent changed
                    continue

                updated.add(col_name)
                tracking_value_ids.extend(
                    [0, 0, self.env['mail.tracking.value']._create_tracking_values_property(
                        property_, col_name, tracked_fields[col_name], self,
                    )]
                    # Show the properties in the same order as in the definition
                    for property_ in initial_value[::-1]
                    if property_['type'] not in ('separator', 'html') and property_.get('value')
                )
                continue

            updated.add(col_name)
            tracking_value_ids.append(
                [0, 0, self.env['mail.tracking.value']._create_tracking_values(
                    initial_value, new_value,
                    col_name, tracked_fields[col_name],
                    self
                )])

        return updated, tracking_value_ids

    def _mail_track_order_fields(self, tracked_fields):
        """ Order tracking, based on sequence found on field definition. When
        having several identical sequences, properties are added after,
        and then field name is used. """
        fields_track_info = [
            (col_name, self._mail_track_get_field_sequence(col_name))
            for col_name in tracked_fields.keys()
        ]
        # sorting: sequence ASC, name ASC (higher sequence -> displayed last, then
        # order by name). Model order being id DESC (aka: first insert -> last
        # displayed) insert should be done by descending sequence then descending
        # name.
        fields_track_info.sort(key=lambda item: (
            item[1],
            tracked_fields[item[0]]['type'] != 'properties',
            item[0],
        ), reverse=True)
        return fields_track_info

    def _mail_track_get_field_sequence(self, fname):
        """ Find tracking sequence of a given field, given their name. Current
        parameter 'tracking' should be an integer, but attributes with True
        are still supported; old naming 'track_sequence' also. """
        if fname not in self._fields:
            return 100

        def get_field_sequence(fname):
            return getattr(
                self._fields[fname], 'tracking',
                getattr(self._fields[fname], 'track_sequence', True)
            )

        sequence = get_field_sequence(fname)
        if self._fields[fname].type == 'properties' and sequence is True:
            # default properties sequence is after the definition record
            parent_sequence = get_field_sequence(self._fields[fname].definition_record)
            return 100 if parent_sequence is True else parent_sequence
        return 100 if sequence is True else sequence

    def _message_add_default_recipients(self):
        """ Generic implementation for finding default recipient to mail on
        a recordset. This method is a generic implementation available for
        all models as we could send an email through mail templates on models
        not inheriting from mail.thread. For that purpose we use mail methods
        to find partners (customers) and primary emails.

        Override this method on a specific model to implement model-specific
        behavior. """
        res = {}
        customers = self._mail_get_partners()
        primary_emails = self._mail_get_primary_email()
        for record in self:
            email_cc_lst, email_to_lst = [], []
            # consider caller is going to filter / handle so don't filter anything
            recipients_all = customers.get(record.id)
            # to computation
            email_to = primary_emails[record.id]
            if not email_to:
                email_to = next(
                    (
                        record[fname] for fname in [
                            'email_from', 'x_email_from',
                            'email', 'x_email',
                            'partner_email',
                            'email_normalized',
                        ] if fname and fname in record and record[fname]
                    ), False
                )
            if email_to:
                # keep value to ease debug / trace update if cannot normalize
                email_to_lst = tools.mail.email_split_and_format_normalize(email_to) or [email_to]
            # cc computation
            cc_fn = next(
                (
                    fname for fname in ['email_cc', 'partner_email_cc', 'x_email_cc']
                    if fname in record and record[fname]
                ), False
            )
            if cc_fn:
                email_cc_lst = tools.mail.email_split_and_format_normalize(record[cc_fn]) or [record[cc_fn]]

            res[record.id] = {
                'email_cc_lst': email_cc_lst,
                'email_to_lst': email_to_lst,
                'partners': recipients_all,
            }
        return res

    def _message_get_default_recipients(self, with_cc=False, all_tos=False):
        """ Compute and filter default recipients to mail on a recordset.
        Heuristics is to find a customer (res.partner record) holding a
        email. Then we fallback on email fields, beginning with field optionally
        defined using `_primary_email` attribute. Email can be prioritized
        compared to partner if `_mail_defaults_to_email` class parameter is set.

        :param with_cc: take into account CC-like field. By default those are
          not considered as valid for 'default recipients' e.g. in mailings,
          automated actions, ...
        :param all_tos: DEPRECATED
        """
        def email_key(email):
            return email_normalize(email, strict=False) or email.strip()

        res = {}
        prioritize_email = getattr(self, '_mail_defaults_to_email', False)
        found = self._message_add_default_recipients()

        # ban emails: never propose odoobot nor aliases
        all_emails = []
        for defaults in found.values():
            all_emails += defaults['email_to_lst']
            if with_cc:
                all_emails += defaults['email_cc_lst']
            all_emails += defaults['partners'].mapped('email_normalized')
        ban_emails = [self.env.ref('base.partner_root').email_normalized]
        ban_emails += self.env['mail.alias.domain'].sudo()._find_aliases(
            [email_key(e) for e in all_emails if e and e.strip()]
        )

        # fetch default recipients for each record
        for record in self:
            defaults = found[record.id]
            customers = defaults['partners']
            email_cc_lst = defaults['email_cc_lst'] if with_cc else []
            email_to_lst = defaults['email_to_lst']

            # pure default recipients, skip public and banned emails
            recipients_all = customers.filtered(lambda p: not p.is_public and (not p.email_normalized or p.email_normalized not in ban_emails))
            recipients = customers.filtered(lambda p: not p.is_public and p.email_normalized and p.email_normalized not in ban_emails)
            # filter emails, skip banned mails
            email_cc_lst = [e for e in email_cc_lst if e not in ban_emails]
            email_to_lst = [e for e in email_to_lst if e not in ban_emails]

            # prioritize recipients: default unless asked through '_mail_defaults_to_email', or when no email_to
            if not prioritize_email or not email_to_lst:
                # if no valid recipients nor emails, fallback on recipients even
                # invalid to have at least some information
                if recipients:
                    partner_ids = recipients.ids
                    email_to = ''
                elif recipients_all and len(recipients_all) == len(email_to_lst) and all(
                    email in recipients_all.mapped('email') for email in email_to_lst
                ):
                    # here we just have partners with invalid emails, same as email fields
                    partner_ids = recipients_all.ids
                    email_to = ''
                else:
                    partner_ids = [] if email_to_lst else recipients_all.ids
                    email_to = ','.join(email_to_lst)
            # if emails match partners, use partners to have more information
            elif len(email_to_lst) == len(recipients) and all(
                tools.email_normalize(email) in recipients.mapped('email_normalized') for email in email_to_lst
            ):
                partner_ids = recipients.ids
                email_to = ''
            else:
                partner_ids = []
                email_to = ','.join(email_to_lst)
            res[record.id] = {
                'email_cc': ','.join(email_cc_lst),
                'email_to': email_to,
                'partner_ids': partner_ids,
            }
        return res

    def _message_add_suggested_recipients(self, force_primary_email=False):
        """ Generic implementation for finding suggested recipient to mail on
        a recordset. """
        suggested = {
            record.id: {'email_to_lst': [], 'partners': self.env['res.partner']}
            for record in self
        }
        defaults = self._message_add_default_recipients()

        # add responsible
        user_field = self._fields.get('user_id')
        if user_field and user_field.type == 'many2one' and user_field.comodel_name == 'res.users':
            # SUPERUSER because of a read on res.users that would crash otherwise
            for record_su in self.sudo():
                suggested[record_su.id]['partners'] += record_su.user_id.partner_id

        # add customers
        for record_id, values in defaults.items():
            suggested[record_id]['partners'] |= values['partners']

        # add email
        for record in self:
            if force_primary_email:
                suggested[record.id]['email_to_lst'] += tools.mail.email_split_and_format_normalize(force_primary_email)
            else:
                suggested[record.id]['email_to_lst'] += defaults[record.id]['email_to_lst']

        return suggested

    def _message_get_suggested_recipients_batch(self, reply_discussion=False, reply_message=None,
                                                no_create=True, primary_email=False, additional_partners=None):
        """ Get suggested recipients, contextualized depending on discussion.
        This method automatically filters out emails and partners linked to
        aliases or alias domains.

        :param bool reply_discussion: consider user replies to the discussion.
          Last relevant message is fetched and used to search for additional
          'To' and 'Cc' to propose;
        :param <mail.message> reply_message: specific message user is replying-to.
          Bypasses 'reply_discussion';
        :param bool no_create: do not create partners when emails are not linked
          to existing partners, see '_partner_find_from_emails';
        :param bool primary_email: new primary_email that isn't stored inside DB;
        :param bool additional_partners: partners that needs to be added to the suggested recipients;

        :returns: list of dictionaries (per suggested recipient) containing:
            * create_values:         dict: data to populate new partner, if not found
            * email:                 str: email of recipient
            * name:                  str: name of the recipient
            * partner_id:            int: recipient partner id
        """
        def email_key(email):
            return email_normalize(email, strict=False) or email.strip()
        is_mail_thread = 'message_partner_ids' in self
        suggested_record = self._message_add_suggested_recipients(force_primary_email=primary_email)

        # copy suggested based on records, then add those from context
        suggested = {}
        for record in self:
            suggested[record.id] = {
                'email_to_lst': suggested_record[record.id]['email_to_lst'].copy(),
                'partners': suggested_record[record.id]['partners'] + (additional_partners or self.env['res.partner']),
            }

        # find last relevant message
        messages = self.env['mail.message']
        if reply_discussion and 'message_ids' in self:
            messages = self._sort_suggested_messages(self.message_ids)
        # fetch answer-based recipients as well as author
        if reply_message or messages:
            for record in self:
                record_msg = reply_message or next(
                    (msg for msg in messages if msg.res_id == record.id and msg.message_type in ('comment', 'email')),
                    self.env['mail.message']
                )
                if not record_msg:
                    continue
                # direct recipients, and author if not archived / root
                suggested[record.id]['partners'] += (record_msg.partner_ids | record_msg.author_id).filtered(lambda p: p.active)
                # To and Cc emails (mainly for incoming email), and email_from if not linked to hereabove author
                suggested[record.id]['email_to_lst'] += [record_msg.incoming_email_to or '', record_msg.incoming_email_cc or '', record_msg.email_from or '']
                from_normalized = email_normalize(record_msg.email_from)
                if from_normalized and from_normalized != record_msg.author_id.email_normalized:
                    suggested[record.id]['email_to_lst'].append(record_msg.email_from)

        # make a record-based list of emails to give to '_partner_find_from_emails'
        records_emails = {}
        all_emails = set()
        for record in self:
            email_to_lst, partners = suggested[record.id]['email_to_lst'], suggested[record.id]['partners']
            # organize and deduplicate partners, exclude followers, keep ordering
            followers = record.message_partner_ids if is_mail_thread else record.env['res.partner']
            # sanitize email inputs, exclude followers and aliases, add some banned emails, keep ordering, then link to partners
            skip_emails_normalized = (followers | partners).mapped('email_normalized') + (followers | partners).mapped('email')
            records_emails[record] = [
                e for email_input in email_to_lst for e in email_split_and_format(email_input)
                if e and e.strip() and email_key(e) not in skip_emails_normalized
            ]
            all_emails |= set(records_emails[record]) | set(partners.mapped('email_normalized'))
        # ban emails: never propose odoobot nor aliases
        ban_emails = [self.env.ref('base.partner_root').email_normalized]
        ban_emails += self.env['mail.alias.domain'].sudo()._find_aliases(
            [email_key(e) for e in all_emails if e and e.strip()]
        )
        thread_recs = self if is_mail_thread else self.env['mail.thread']
        records_partners = thread_recs._partner_find_from_emails(
            records_emails,
            # already computed in ban_emails, no need to re-check aliases
            avoid_alias=False, ban_emails=ban_emails,
            no_create=no_create,
        )

        # final filtering, and fetch model-related additional information for create values
        emails_normalized_info = self._get_customer_information() if is_mail_thread else {}
        suggested_recipients = {}
        for record in self:
            followers = record.message_partner_ids if is_mail_thread else record.env['res.partner']
            partners = self.env['res.partner'].browse(tools.misc.unique(
                p.id for p in (suggested[record.id]['partners'] + records_partners[record.id])
                if (
                    # skip followers, unless being a customer suggested by record (mostly defaults)
                    (
                        p not in followers or (
                            p in suggested_record[record.id]['partners'] and
                            p.partner_share
                    )) and
                    p.email_normalized not in ban_emails and
                    not p.is_public
                )
            ))
            existing_mails = {
                email_key(e)
                for rec in (followers | partners)
                for e in ([rec.email_normalized] if rec.email_normalized else []) + email_split_and_format(rec.email or '')
            }
            email_to_lst = list(tools.misc.unique(
                e for email_input in suggested[record.id]['email_to_lst'] for e in email_split_and_format(email_input)
                if (
                    e and e.strip() and
                    email_key(e) not in ban_emails and
                    email_key(e) not in existing_mails
                )
            ))

            recipients = [{
                **({'display_name': partner.display_name} if not partner.name else {}),
                'email': partner.email_normalized,
                'name': partner.name,
                'partner_id': partner.id,
                'create_values': {},
            } for partner in partners]
            for email_input in email_to_lst:
                name, email_normalized = parse_contact_from_email(email_input)
                recipients.append({
                    'email': email_normalized,
                    'name': emails_normalized_info.get(email_normalized, {}).pop('name', False) or name,
                    'partner_id': False,
                    'create_values': emails_normalized_info.get(email_normalized, {}),
                })
            suggested_recipients[record.id] = recipients
        return suggested_recipients

    def _sort_suggested_messages(self, messages):
        """ Sort messages for suggestion. Keep only discussions: incoming email
        or user comments, with subtype being 'comment' to exclude notes,
        logs, trackings, ... then take the most recent one. If no matching
        message is found, no suggested message is given, as other messages
        should not trigger a 'reply-all' behavior.

        Dedicated method to ease override and csutom behavior for filtering
        and sorting messages in '_message_get_suggested_recipients' """
        subtype_ids = self._creation_subtype().ids if hasattr(self, '_creation_subtype') else []
        subtype_ids.append(self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'))
        return messages.filtered(
            lambda msg: (
                msg.message_type in ('email', 'comment') and
                msg.subtype_id.id in subtype_ids
            )
        ).sorted(lambda msg: (msg.date, msg.id), reverse=True)

    def _message_get_suggested_recipients(self, reply_discussion=False, reply_message=None,
                                            no_create=True, primary_email=False, additional_partners=None):
        self.ensure_one()
        return self._message_get_suggested_recipients_batch(
            reply_discussion=reply_discussion, reply_message=reply_message,
            no_create=no_create, primary_email=primary_email, additional_partners=additional_partners,
        )[self.id]

    def _notify_get_reply_to(self, default=None, author_id=False):
        """ Returns the preferred reply-to email address when replying to a thread
        on documents. This method is a generic implementation available for
        all models as we could send an email through mail templates on models
        not inheriting from mail.thread.

        Reply-to is formatted like '"Author Name" <reply.to@domain>".
        Heuristic it the following:

        * search for specific aliases as they always have priority; it is limited
          to aliases linked to documents (like project alias for task for example);
        * use catchall address;
        * use default;

        This method can be used as a generic tools if self is a void recordset.

        :param default: default email if no alias or catchall is found;
        :param author_id: author to use in name part of formatted email;

        :return: dictionary. Keys are record IDs and value is formatted
          like an email "Company_name Document_name <reply_to@email>"
        """
        return self._notify_get_reply_to_batch(
            defaults={res_id: default for res_id in (self.ids or [False])},
            author_ids={res_id: author_id for res_id in (self.ids or [False])},
        )

    def _notify_get_reply_to_batch(self, defaults=None, author_ids=None):
        """ Batch-enabled version of '_notify_get_reply_to' where default and
        author_id may be different / record. This one exist mainly for batch
        intensive computation like composer in mass mode, where email configuration
        is different / record due to dynamic rendering.

        :param dict defaults: default / record ID;
        :param dict author_ids: author ID / record ID;
        """
        _records = self
        model = _records._name if _records and _records._name != 'mail.thread' else False
        res_ids = _records.ids if _records and model else []
        _res_ids = res_ids or [False]  # always have a default value located in False
        _records_sudo = _records.sudo()
        if defaults is None:
            defaults = dict.fromkeys(_res_ids, False)
        if author_ids is None:
            author_ids = dict.fromkeys(_res_ids, False)

        # sanity check
        if set(defaults.keys()) != set(_res_ids):
            raise ValueError(f'Invalid defaults, keys {defaults.keys()} does not match recordset IDs {_res_ids}')
        if set(author_ids.keys()) != set(_res_ids):
            raise ValueError(f'Invalid author_ids, keys {author_ids.keys()} does not match recordset IDs {_res_ids}')

        # group ids per company
        if res_ids:
            company_to_res_ids = defaultdict(list)
            record_ids_to_company = _records_sudo._mail_get_companies(default=self.env.company)
            for record_id, company in record_ids_to_company.items():
                company_to_res_ids[company].append(record_id)
        else:
            company_to_res_ids = {self.env.company: _res_ids}
            record_ids_to_company = {_res_id: self.env.company for _res_id in _res_ids}

        # begin with aliases (independent from company, alias_domain_id on alias wins)
        reply_to_email = {}
        if model and res_ids:
            mail_aliases = self.env['mail.alias'].sudo().search([
                ('alias_domain_id', '!=', False),
                ('alias_parent_model_id.model', '=', model),
                ('alias_parent_thread_id', 'in', res_ids),
                ('alias_name', '!=', False)
            ])
            # take only first found alias for each thread_id, to match order (1 found -> limit=1 for each res_id)
            for alias in mail_aliases:
                reply_to_email.setdefault(alias.alias_parent_thread_id, alias.alias_full_name)

        # continue with company alias
        left_ids = set(_res_ids) - set(reply_to_email)
        if left_ids:
            for company, record_ids in company_to_res_ids.items():
                # left ids: use catchall defined on company alias domain
                if company.catchall_email:
                    left_ids = set(record_ids) - set(reply_to_email)
                    if left_ids:
                        reply_to_email.update({rec_id: company.catchall_email for rec_id in left_ids})

        # compute name of reply-to ("Company Document" <alias@domain>)
        reply_to_formatted = dict(defaults)
        for res_id, record_reply_to in reply_to_email.items():
            reply_to_formatted[res_id] = self._notify_get_reply_to_formatted_email(
                record_reply_to,
                author_id=author_ids[res_id],
            )

        return reply_to_formatted

    def _notify_get_reply_to_formatted_email(self, record_email, author_id=False):
        """ Compute formatted email for reply_to and try to avoid refold issue
        with python that splits the reply-to over multiple lines. It is due to
        a bad management of quotes (missing quotes after refold). This appears
        therefore only when having quotes (aka not simple names, and not when
        being unicode encoded).
        Another edge-case produces a linebreak (CRLF) immediately after the
        colon character separating the header name from the header value.
        This creates an issue in certain DKIM tech stacks that will
        incorrectly read the reply-to value as empty and fail the verification.

        To avoid that issue when formataddr would return more than 68 chars we
        return a simplified name/email to try to stay under 68 chars. If not
        possible we return only the email and skip the formataddr which causes
        the issue in python. We do not use hacks like crop the name part as
        encoding and quoting would be error prone.
        """
        length_limit = 68  # 78 - len('Reply-To: '), 78 per RFC
        # address itself is too long : return only email and log warning
        if len(record_email) >= length_limit:
            _logger.warning('Notification email address for reply-to is longer than 68 characters. '
                'This might create non-compliant folding in the email header in certain DKIM '
                'verification tech stacks. It is advised to shorten it if possible. '
                'Reply-To: %s ', record_email)
            return record_email

        if author_id:
            author_name = self.env['res.partner'].browse(author_id).name
        else:
            author_name = self.env.user.name

        # try user.name alone, then company.name alone
        formatted_email = tools.formataddr((author_name, record_email))
        if len(formatted_email) > length_limit:
            formatted_email = tools.formataddr((self.env.user.name, record_email))
        if len(formatted_email) > length_limit:
            formatted_email = record_email
        return formatted_email

    # ------------------------------------------------------------
    # ALIAS MANAGEMENT
    # ------------------------------------------------------------

    def _alias_get_error(self, message, message_dict, alias):
        """ Generic method that takes a record not necessarily inheriting from
        mail.alias.mixin.

        :return: error if any, False otherwise
        :rtype: AliasError | Literal[False]
        """
        author = self.env['res.partner'].browse(message_dict.get('author_id', False))
        if alias.alias_contact == 'followers':
            if not self.ids:
                return AliasError('config_follower_no_record',
                                  _('incorrectly configured alias (unknown reference record)'),
                                  is_config_error=True)
            if not hasattr(self, "message_partner_ids"):
                return AliasError('config_follower_no_partners', _('incorrectly configured alias'), True)
            if not author or author not in self.message_partner_ids:
                return AliasError('error_follower_not_following', _('restricted to followers'))
        elif alias.alias_contact == 'partners' and not author:
            return AliasError('error_partners_no_partner', _('restricted to known authors'))
        return False

    # ------------------------------------------------------------
    # ACTIVITY
    # ------------------------------------------------------------

    @api.model
    def _get_default_activity_view(self):
        """ Generates an empty activity view.

        :returns: a activity view as an lxml document
        :rtype: etree._Element
        """
        field = E.field(name=self._rec_name_fallback())
        activity_box = E.div(field, {'t-name': "activity-box"})
        templates = E.templates(activity_box)
        return E.activity(templates, string=self._description)

    # ------------------------------------------------------------
    # DISCUSS
    # ------------------------------------------------------------

    def _mail_get_message_subtypes(self):
        return self.env['mail.message.subtype'].search([
            '&', ('hidden', '=', False),
            '|', ('res_model', '=', self._name), ('res_model', '=', False)])

    # ------------------------------------------------------------
    # GATEWAY: NOTIFICATION
    # ------------------------------------------------------------

    def _notify_by_email_get_headers(self, headers=None):
        """ Generate the email headers based on record. Each header not already
        present in 'headers' will be added in it. """
        headers = headers or {}
        if not self:
            return headers
        self.ensure_one()
        headers['X-Odoo-Objects'] = f"{self._name}-{self.id}"
        if 'Return-Path' not in headers:
            company = self._mail_get_companies(default=self.env.company)[self.id]
            if company.bounce_email:
                headers['Return-Path'] = company.bounce_email
        return headers

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _get_html_link(self, title=None):
        """Generate the record html reference for chatter use.

        :param str title: optional reference title, the record display_name
            is used if not provided. The title/display_name will be escaped.
        :returns: generated html reference,
            in the format <a href data-oe-model="..." data-oe-id="...">title</a>
        :rtype: str
        """
        self.ensure_one()
        return Markup("<a href=# data-oe-model='%s' data-oe-id='%s'>%s</a>") % (
            self._name, self.id, title or self.display_name)

    @api.model
    def _get_backend_root_menu_ids(self):
        """ Method meant to be overridden to define the root menu for the model.

        When overriding this method, call super and then add the menu id of your
        module so that the menu id related to the most specialized will be at the
        end of the list.
        """
        return []

    def _find_value_from_field_path(self, field_path):
        """Get the value of field, returning display_name(s) if the field is a
        model. Can be called on a void recordset, in which case it mainly serves
        as a field path validation."""
        if self:
            self.ensure_one()

        # as we use mapped(False) returns record, better return a void string
        if not field_path:
            return ''

        try:
            field_value = self.mapped(field_path)
        except KeyError:
            raise exceptions.UserError(
                _("%(model_name)s.%(field_path)s does not seem to be a valid field path", model_name=self._name, field_path=field_path)
            )
        except Exception as err:  # noqa: BLE001
            raise exceptions.UserError(
                _("We were not able to fetch value of field '%(field)s'", field=field_path)
            ) from err
        if isinstance(field_value, models.Model):
            return ' '.join((value.display_name or '') for value in field_value)
        if any(isinstance(value, datetime) for value in field_value):
            tz = (self and self._mail_get_timezone()) or self.env.user.tz or 'UTC'
            return ' '.join([f"{tools.format_datetime(self.env, value, tz=tz)} {tz}"
                             for value in field_value if value and isinstance(value, datetime)])
        # find last field / last model when having chained fields
        # e.g. 'partner_id.country_id.state' -> ['partner_id.country_id', 'state']
        field_path_models = field_path.rsplit('.', 1)
        if len(field_path_models) > 1:
            last_model_path, last_fname = field_path_models
            last_model = self.mapped(last_model_path)
        else:
            last_model, last_fname = self, field_path
        last_field = last_model._fields[last_fname]
        # if selection -> return value, not the key
        if last_field.type == 'selection':
            return ' '.join(
                last_field.convert_to_export(value, last_model)
                for value in field_value
            )
        return ' '.join(str(value if value is not False and value is not None else '') for value in field_value)

    def _mail_get_timezone(self):
        """To be overridden to get desired timezone of the model.

        :returns: selected timezone (e.g. 'UTC' or 'Asia/Kolkata')
        """
        self.ensure_one()
        return next(filter(
            None,
            (self[tz_field] for tz_field in ('date_tz', 'tz', 'timezone') if tz_field in self)
        ), None)
