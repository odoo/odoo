# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime
from lxml.builder import E
from markupsafe import Markup

from odoo import api, exceptions, models, tools, _
from odoo.addons.mail.tools.alias_error import AliasError

import logging

_logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = 'base'
    _mail_defaults_to_email = False

    def _valid_field_parameter(self, field, name):
        # allow tracking on abstract models; see also 'mail.thread'
        return (
            name == 'tracking' and self._abstract
            or super()._valid_field_parameter(field, name)
        )

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

    def _mail_get_partners(self, introspect_fields=False):
        """ Give the default partners (customers) associated to customers.

        :param bool introspect_fields: see '_mail_get_partner_fields';

        :return: for each record ID, a res.partner recordsets being default
          customers to contact;
        """
        partner_fields = self._mail_get_partner_fields(introspect_fields=introspect_fields)
        pids = {pid for record in self for fn in partner_fields for pid in record[fn].ids}
        Partner = self.env['res.partner'].with_prefetch(pids)
        records_partners = {}
        for record in self:
            pids = tools.unique(pid for fn in partner_fields for pid in record[fn].ids)
            records_partners[record.id] = Partner.browse(pids)
        return records_partners

    @api.model
    def _mail_get_primary_email_field(self):
        """ Check if the "_primary_email" model attribute is correctly set and
        matches an existing field, and return it. Otherwise return None. """
        primary_email = getattr(self, '_primary_email', None)
        if primary_email and primary_email in self._fields:
            return primary_email
        return None

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
            initial_value, new_value = initial_values[col_name], self[col_name]
            if new_value == initial_value or (not new_value and not initial_value):  # because browse null != False
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
        having several identical sequences, field name is used. """
        fields_track_info = [
            (col_name, self._mail_track_get_field_sequence(col_name))
            for col_name in tracked_fields.keys()
        ]
        # sorting: sequence ASC, name ASC (higher sequence -> displayed last, then
        # order by name). Model order being id DESC (aka: first insert -> last
        # displayed) insert should be done by descending sequence then descending
        # name.
        fields_track_info.sort(key=lambda item: (item[1], item[0]), reverse=True)
        return fields_track_info

    def _mail_track_get_field_sequence(self, fname):
        """ Find tracking sequence of a given field, given their name. Current
        parameter 'tracking' should be an integer, but attributes with True
        are still supported; old naming 'track_sequence' also. """
        sequence = getattr(
            self._fields[fname], 'tracking',
            getattr(self._fields[fname], 'track_sequence', 100)
        )
        if sequence is True:
            sequence = 100
        return sequence

    def _message_get_default_recipients(self):
        """ Generic implementation for finding default recipient to mail on
        a recordset. This method is a generic implementation available for
        all models as we could send an email through mail templates on models
        not inheriting from mail.thread.

        Heuristics is to find a customer (res.partner record) holding a
        email. Then we fallback on email fields, beginning with field optionally
        defined using `_primary_email` attribute. Email can be prioritized
        compared to partner if `_mail_defaults_to_email` class parameter is set.

        Override this method on a specific model to implement model-specific
        behavior. Also consider inheriting from ``mail.thread``. """
        include_cc = self.env.context.get('mail_recipients_include_cc')
        res = {}
        customers = self._mail_get_partners()
        prioritize_email = getattr(self, '_mail_defaults_to_email', False)
        primary_email_fn = self._mail_get_primary_email_field()
        for record in self:
            email_cc_lst, email_to_lst = [], []
            # main recipients (res.partner)
            recipients_all = customers.get(record.id).filtered(lambda p: not p.is_public)
            recipients = recipients_all.filtered(lambda p: p.email)
            # to computation
            to_fn = next(
                (
                    fname for fname in [
                        primary_email_fn,
                        'email_from', 'x_email_from',
                        'email', 'x_email',
                        'partner_email',
                        'email_normalized',
                    ] if fname and fname in record and record[fname]
                ), False
            )
            if to_fn:
                # keep value to ease debug / trace update if cannot normalize
                email_to_lst = tools.mail.email_split_and_format_normalize(record[to_fn]) or [record[to_fn]]
            # cc computation
            cc_fn = next(
                (
                    fname for fname in ['email_cc', 'partner_email_cc', 'x_email_cc']
                    if fname in record and record[fname]
                ), False
            ) if include_cc else ''
            if cc_fn:
                email_cc_lst = tools.mail.email_split_and_format_normalize(record[cc_fn]) or [record[cc_fn]]
            # prioritize recipients: default, or when to == recipients emails, or
            # when no email_to
            if not prioritize_email or not email_to_lst:
                # if no valid recipients nor emails, fallback on recipients even
                # invalid to have at least some information
                if recipients:
                    partner_ids = recipients.ids or recipients_all.ids
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

    def _notify_get_reply_to(self, default=None):
        """ Returns the preferred reply-to email address when replying to a thread
        on documents. This method is a generic implementation available for
        all models as we could send an email through mail templates on models
        not inheriting from mail.thread.

        Reply-to is formatted like "MyCompany MyDocument <reply.to@domain>".
        Heuristic it the following:
         * search for specific aliases as they always have priority; it is limited
           to aliases linked to documents (like project alias for task for example);
         * use catchall address;
         * use default;

        This method can be used as a generic tools if self is a void recordset.

        Override this method on a specific model to implement model-specific
        behavior. Also consider inheriting from ``mail.thread``.
        An example would be tasks taking their reply-to alias from their project.

        :param default: default email if no alias or catchall is found;
        :return result: dictionary. Keys are record IDs and value is formatted
          like an email "Company_name Document_name <reply_to@email>"/
        """
        _records = self
        model = _records._name if _records and _records._name != 'mail.thread' else False
        res_ids = _records.ids if _records and model else []
        _res_ids = res_ids or [False]  # always have a default value located in False
        _records_sudo = _records.sudo()
        doc_names = {rec.id: rec.display_name for rec in _records_sudo} if res_ids else {}

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
        reply_to_formatted = dict.fromkeys(_res_ids, default)
        for res_id, record_reply_to in reply_to_email.items():
            reply_to_formatted[res_id] = self._notify_get_reply_to_formatted_email(
                record_reply_to, doc_names.get(res_id) or '', company=record_ids_to_company[res_id],
            )

        return reply_to_formatted

    def _notify_get_reply_to_formatted_email(self, record_email, record_name, company=False):
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

        :param <res.company> company: if given, setup the company used to
          complete name in formataddr. Otherwise fallback on 'company_id'
          of self or environment company;
        """
        length_limit = 68  # 78 - len('Reply-To: '), 78 per RFC
        # address itself is too long : return only email and log warning
        if len(record_email) >= length_limit:
            _logger.warning('Notification email address for reply-to is longer than 68 characters. '
                'This might create non-compliant folding in the email header in certain DKIM '
                'verification tech stacks. It is advised to shorten it if possible. '
                'Record name (if set): %s '
                'Reply-To: %s ', record_name, record_email)
            return record_email

        if not company:
            if len(self) == 1:
                company = self.sudo()._mail_get_companies(default=self.env.company)
            else:
                company = self.env.company

        # try company.name + record_name, or record_name alone (or company.name alone)
        name = f"{company.name} {record_name}" if record_name else company.name

        formatted_email = tools.formataddr((name, record_email))
        if len(formatted_email) > length_limit:
            formatted_email = tools.formataddr((record_name or company.name, record_email))
        if len(formatted_email) > length_limit:
            formatted_email = record_email
        return formatted_email

    # ------------------------------------------------------------
    # ALIAS MANAGEMENT
    # ------------------------------------------------------------

    def _alias_get_error(self, message, message_dict, alias):
        """ Generic method that takes a record not necessarily inheriting from
        mail.alias.mixin.

        :return AliasError: error if any, False otherwise
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
            tz = self._mail_get_timezone()
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
        """To be override to get desired timezone of the model

        :returns: selected timezone (e.g. 'UTC' or 'Asia/Kolkata')
        """
        if self:
            self.ensure_one()
        tz = self.env.user.tz or 'UTC'
        for tz_field in ('date_tz', 'tz', 'timezone'):
            if tz_field in self:
                tz = self[tz_field] or tz
        return tz
