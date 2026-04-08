from __future__ import annotations

import hashlib
import hmac
import logging

from werkzeug.urls import url_encode

from odoo import _, api, models

_logger = logging.getLogger(__name__)


class MailNotifyMixin(models.AbstractModel):
    """ Base class enabling notifications on models using the static methods of mail.thread."""
    _name = 'mail.notify.mixin'
    _description = 'Mail Notify Mixin'

    _CUSTOMER_HEADERS_LIMIT_COUNT = 0

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        """ Return groups used to classify recipients of a notification email.
        Groups is a list of tuple (group_name, group_func, group_data) where

         * 'group_name' is an identifier used only to be able to override and
           manipulate groups;
         * 'group_func' is a function pointer taking a partner data dict as
           parameter. It is called on recipients to know if they belong to
           the group. Only first matching group is kept, iterating on the
           group list in order.
         * 'group_data' is a dict containing parameters used in notification
           process like {
            'active': if not, it is skipped in notification process (ease
                      inheritance to be already present);
            'button_access': main access document button information, {'url'
                             link of the access, 'title': link or button
                             string};
            'has_button_access': display access document main button in email;
            'notification_group_name': name of the group, to ease usage;
            'recipients_data': list of recipients data, following format used
                               in '_notify_get_recipients'. It is fillup when
                               evaluating groups;
            'recipients_ids': list of partner IDs, based on partner ID present in
                              recipients_data (allows mainly to speedup some
                              data computation);
           }

        Default groups:

          * 'user': recipients linked to an internal user;
          * 'portal': recipients linked to a portal user;
          * 'follower': recipients (not internal/portal users) follower of the
            related record;
          * 'customer': other recipients (always partners);

        When having to find a group for recipients, the first matching one
        when iterating on groups is used. Reordering those groups is doable
        through override. Adding groups is a common override, to add specific
        buttons for users belonging to some user groups.

        :param record message: <mail.message> record being notified. May be
          void as 'msg_vals' supersedes it;
        :param str model_description: description of current model, given to
          avoid fetching it and easing translation support;
        :param dict msg_vals: values dict used to create the message, allows to
          skip message usage and spare some queries if given;

        :return: list of groups definition
        """
        return [
            [
                'user',
                lambda pdata: pdata['type'] == 'user',
                {
                    'active': True,
                    'has_button_access': self.env['mail.message']._is_thread_message(vals=msg_vals, thread=self),
                }
            ], [
                'portal',
                lambda pdata: pdata['type'] == 'portal',
                {
                    'active': False,  # activate only on demand if rights are enabled
                    'has_button_access': False,
                }
            ], [
                'follower',
                lambda pdata: pdata['is_follower'],
                {
                    'active': False,  # activate only on demand if rights are enabled
                    'has_button_access': False,
                }
            ], [
                'customer',
                lambda pdata: True,
                {
                    'active': True,
                    'has_button_access': False,
                }
            ],
        ]

    def _notify_get_recipients_groups_fillup(self, groups, model_description, msg_vals=False):
        """ Iterate on recipients groups (see '_notify_get_recipients_groups')
        and fill up the result with default values, allowing to compute links or
        titles once.

        :param list groups: recipients groups;
        :param dict msg_vals: values dict used to create the message, allows to
          skip message usage and spare some queries if given;
        :param str model_description: description of current model, given to
          avoid fetching it and easing translation support;

        :return: updated groups;
        """
        access_link = self._notify_get_action_link('view', **msg_vals)

        if model_description:
            view_title = _('View %s', model_description)
        else:
            view_title = _('View')

        is_thread_message = self.env['mail.message']._is_thread_message(vals=msg_vals, thread=self)

        # fill group_data with default_values if they are not complete
        for group_name, _group_func, group_data in groups:
            group_data.setdefault('active', True)
            group_data.setdefault('has_button_access', is_thread_message)
            group_data.setdefault('notification_group_name', group_name)
            group_data.setdefault('recipients_data', [])
            group_data.setdefault('recipients_emails', [])
            group_data.setdefault('recipients_ids', [])
            group_button_access = group_data.setdefault('button_access', {})
            group_button_access.setdefault('url', access_link)
            group_button_access.setdefault('title', view_title)

        return groups

    def _notify_get_recipients_classify(self, message, recipients_data,
                                        model_description, msg_vals=False):
        """ Classify recipients to be notified of a message in groups to have
        specific rendering depending on their group. For example users could
        have access to buttons customers should not have in their emails.
        Module-specific grouping should be done by overriding ``_notify_get_recipients_groups``
        method defined here-under.

        :param record message: <mail.message> record being notified. May be
          void as 'msg_vals' superseeds it;
        :param list recipients_data: list of recipients data based on <res.partner>
          records formatted like a list of dicts containing information. See
          ``MailThread._notify_get_recipients()``;
        :param str model_description: description of current model, given to
          avoid fetching it and easing translation support;
        :param dict msg_vals: values dict used to create the message, allows to
          skip message usage and spare some queries if given;

        :return: list of groups (see '_notify_get_recipients_groups')
          with 'recipients' key filled with matching partners, like
            [{
                'active': True,
                'button_access': {'url': 'https://odoo.com/url', 'title': 'Title'},
                'has_button_access': False,
                'notification_group_name': 'user',
                'recipients_data': [{...}],
                'recipients_ids': [11],
             }, {...}]
        :rtype: list[dict]
        """
        # keep a local copy of msg_vals as it may be modified to include more
        # information about groups or links
        local_msg_vals = dict(msg_vals) if msg_vals else {}
        groups = self._notify_get_recipients_groups_fillup(
            self._notify_get_recipients_groups(
                message, model_description, msg_vals=local_msg_vals
            ),
            model_description,
            msg_vals=local_msg_vals
        )
        # sanitize groups
        for _group_name, _group_func, group_data in groups:
            if 'actions' in group_data:
                _logger.warning('Invalid usage of actions in notification groups')

        # classify recipients in each group
        for recipient_data in recipients_data:
            for _group_name, group_func, group_data in groups:
                if group_data['active'] and group_func(recipient_data):
                    group_data['recipients_data'].append(recipient_data)
                    if recipient_data['id']:
                        group_data['recipients_ids'].append(recipient_data['id'])
                    elif recipient_data['email_normalized']:
                        group_data['recipients_emails'].append(recipient_data['email_normalized'])
                    break

        # filter out groups without recipients
        return [
            group_data
            for _group_name, _group_func, group_data in groups
            if group_data['recipients_data']
        ]

    @api.model
    def _notify_get_recipients_for_extra_notifications(self, message, recipients_data, msg_vals=False):
        """ Never send to author and to people outside Odoo (email) except comments """
        notif_pids = []
        notif_pids_notinbox = []
        for recipient in (r for r in recipients_data if r['active'] and r['id']):
            notif_pids.append(recipient['id'])
            if recipient['notif'] != 'inbox':
                notif_pids_notinbox.append(recipient['id'])
        if not notif_pids:
            return []

        msg_vals = msg_vals or {}
        msg_type = msg_vals.get('message_type') or message.sudo().message_type
        author_ids = [msg_vals.get('author_id') or message.sudo().author_id.id]
        if msg_type in {'comment', 'whatsapp_message'}:
            return set(notif_pids) - set(author_ids)
        elif msg_type in ('notification', 'user_notification', 'email'):
            return (set(notif_pids) - set(author_ids) - set(notif_pids_notinbox))
        return []

    def _notify_get_action_link(self, link_type, **kwargs):
        """ Prepare link to an action: view document, follow document, ... """
        params = self._get_action_link_params(link_type, **kwargs)

        if link_type in ['view', 'unfollow']:
            base_link = '/mail/%s' % link_type
        elif link_type == 'controller':
            controller = kwargs.get('controller')
            base_link = '%s' % controller
        else:
            raise NotImplementedError(f'Invalid notification link type {link_type}')

        if link_type != 'view':
            token = self._encode_link(base_link, params)
            params['token'] = token

        link = '%s?%s' % (base_link, url_encode(params, sort=True))
        if self:
            link = self[0].get_base_url() + link

        return link

    # tools and helpers
    # ------------------------------------------------------------

    @api.model
    def _encode_link(self, base_link, params):
        secret = self.env['ir.config_parameter'].sudo().get_str('database.secret')
        token = '%s?%s' % (base_link, ' '.join('%s=%s' % (key, params[key]) for key in sorted(params)))
        hm = hmac.new(secret.encode('utf-8'), token.encode('utf-8'), hashlib.sha1).hexdigest()
        return hm

    def _get_action_link_params(self, link_type, **kwargs):
        """ Parameters management for '_notify_get_action_link' """
        params = {
            'model': kwargs.get('model', self._name),
            'res_id': kwargs.get('res_id', self.ids[0] if self else False),
        }
        # keep only accepted parameters:
        # - action (deprecated), token (assign), access_token (view)
        # - auth_signup: auth_signup_token and auth_login
        # - portal: pid, hash
        params.update({
            key: value
            for key, value in kwargs.items()
            if key in ('action', 'token', 'access_token', 'auth_signup_token',
                       'auth_login', 'pid', 'hash')
        })
        if link_type == 'controller':
            params.pop('model')
        elif link_type not in ['view', 'assign', 'follow', 'unfollow']:
            return {}
        return params
