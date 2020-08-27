# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml.builder import E

from odoo import api, models, tools, _


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    # ------------------------------------------------------------
    # GENERIC MAIL FEATURES
    # ------------------------------------------------------------

    def _mail_track(self, tracked_fields, initial):
        """ For a given record, fields to check (tuple column name, column info)
        and initial values, return a valid command to create tracking values.

        :param tracked_fields: fields_get of updated fields on which tracking
          is checked and performed;
        :param initial: dict of initial values for each updated fields;

        :return: a tuple (changes, tracking_value_ids) where
          changes: set of updated column names;
          tracking_value_ids: a list of ORM (0, 0, values) commands to create
          ``mail.tracking.value`` records;

        Override this method on a specific model to implement model-specific
        behavior. Also consider inheriting from ``mail.thread``. """
        self.ensure_one()
        changes = set()  # contains onchange tracked fields that changed
        tracking_value_ids = []

        # generate tracked_values data structure: {'col_name': {col_info, new_value, old_value}}
        for col_name, col_info in tracked_fields.items():
            if col_name not in initial:
                continue
            initial_value = initial[col_name]
            new_value = self[col_name]

            if new_value != initial_value and (new_value or initial_value):  # because browse null != False
                tracking_sequence = getattr(self._fields[col_name], 'tracking',
                                            getattr(self._fields[col_name], 'track_sequence', 100))  # backward compatibility with old parameter name
                if tracking_sequence is True:
                    tracking_sequence = 100
                tracking = self.env['mail.tracking.value'].create_tracking_values(initial_value, new_value, col_name, col_info, tracking_sequence, self._name)
                if tracking:
                    tracking_value_ids.append([0, 0, tracking])
                changes.add(col_name)

        return changes, tracking_value_ids

    def _message_get_default_recipients(self):
        """ Generic implementation for finding default recipient to mail on
        a recordset. This method is a generic implementation available for
        all models as we could send an email through mail templates on models
        not inheriting from mail.thread.

        Override this method on a specific model to implement model-specific
        behavior. Also consider inheriting from ``mail.thread``. """
        res = {}
        for record in self:
            recipient_ids, email_to, email_cc = [], False, False
            if 'partner_id' in record and record.partner_id:
                recipient_ids.append(record.partner_id.id)
            elif 'email_normalized' in record and record.email_normalized:
                email_to = record.email_normalized
            elif 'email_from' in record and record.email_from:
                email_to = record.email_from
            elif 'partner_email' in record and record.partner_email:
                email_to = record.partner_email
            elif 'email' in record and record.email:
                email_to = record.email
            res[record.id] = {'partner_ids': recipient_ids, 'email_to': email_to, 'email_cc': email_cc}
        return res

    def _notify_get_reply_to(self, default=None, records=None, company=None, doc_names=None):
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
        :param records: DEPRECATED, self should be a valid record set or an
          empty recordset if a generic reply-to is required;
        :param company: used to compute company name part of the from name; provide
          it if already known, otherwise fall back on user company;
        :param doc_names: dict(res_id, doc_name) used to compute doc name part of
          the from name; provide it if already known to avoid queries, otherwise
          name_get on document will be performed;
        :return result: dictionary. Keys are record IDs and value is formatted
          like an email "Company_name Document_name <reply_to@email>"/
        """
        if records:
            raise ValueError('Use of records is deprecated as this method is available on BaseModel.')

        _records = self
        model = _records._name if _records and _records._name != 'mail.thread' else False
        res_ids = _records.ids if _records and model else []
        _res_ids = res_ids or [False]  # always have a default value located in False

        alias_domain = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.domain")
        result = dict.fromkeys(_res_ids, False)
        result_email = dict()
        doc_names = doc_names if doc_names else dict()

        if alias_domain:
            if model and res_ids:
                if not doc_names:
                    doc_names = dict((rec.id, rec.display_name) for rec in _records)

                mail_aliases = self.env['mail.alias'].sudo().search([
                    ('alias_parent_model_id.model', '=', model),
                    ('alias_parent_thread_id', 'in', res_ids),
                    ('alias_name', '!=', False)])
                # take only first found alias for each thread_id, to match order (1 found -> limit=1 for each res_id)
                for alias in mail_aliases:
                    result_email.setdefault(alias.alias_parent_thread_id, '%s@%s' % (alias.alias_name, alias_domain))

            # left ids: use catchall
            left_ids = set(_res_ids) - set(result_email)
            if left_ids:
                catchall = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.alias")
                if catchall:
                    result_email.update(dict((rid, '%s@%s' % (catchall, alias_domain)) for rid in left_ids))

            # compute name of reply-to - TDE tocheck: quotes and stuff like that
            company_name = company.name if company else self.env.company.name
            for res_id in result_email:
                name = '%s%s%s' % (company_name, ' ' if doc_names.get(res_id) else '', doc_names.get(res_id, ''))
                result[res_id] = tools.formataddr((name, result_email[res_id]))

        left_ids = set(_res_ids) - set(result_email)
        if left_ids:
            result.update(dict((res_id, default) for res_id in left_ids))

        return result

    # ------------------------------------------------------------
    # ALIAS MANAGEMENT
    # ------------------------------------------------------------

    def _alias_check_contact(self, message, message_dict, alias):
        """ Deprecated, remove in v14+ """
        error_msg = self._alias_get_error_message(message, message_dict, alias)
        return error_msg if error_msg else True

    def _alias_get_error_message(self, message, message_dict, alias):
        """ Generic method that takes a record not necessarily inheriting from
        mail.alias.mixin. """
        author = self.env['res.partner'].browse(message_dict.get('author_id', False))
        if alias.alias_contact == 'followers':
            if not self.ids:
                return _('incorrectly configured alias (unknown reference record)')
            if not hasattr(self, "message_partner_ids") or not hasattr(self, "message_channel_ids"):
                return _('incorrectly configured alias')
            accepted_partner_ids = self.message_partner_ids | self.message_channel_ids.mapped('channel_partner_ids')
            if not author or author not in accepted_partner_ids:
                return _('restricted to followers')
        elif alias.alias_contact == 'partners' and not author:
            return _('restricted to known authors')
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
    # GATEWAY: NOTIFICATION
    # ------------------------------------------------------------

    def _notify_email_headers(self):
        """
            Generate the email headers based on record
        """
        if not self:
            return {}
        self.ensure_one()
        return repr(self._notify_email_header_dict())

    def _notify_email_header_dict(self):
        return {
            'X-Odoo-Objects': "%s-%s" % (self._name, self.id),
        }
