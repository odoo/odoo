# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid
from werkzeug.urls import url_encode
from odoo import api, exceptions, fields, models, _


class PortalMixin(models.AbstractModel):
    _name = "portal.mixin"
    _description = 'Portal Mixin'

    access_url = fields.Char(
        'Portal Access URL', compute='_compute_access_url',
        help='Customer Portal URL')
    access_token = fields.Char('Security Token', copy=False)

    # to display the warning from specific model
    access_warning = fields.Text("Access warning", compute="_compute_access_warning")

    def _compute_access_warning(self):
        for mixin in self:
            mixin.access_warning = ''

    def _compute_access_url(self):
        for record in self:
            record.access_url = '#'

    def _portal_ensure_token(self):
        """ Get the current record access token """
        if not self.access_token:
            # we use a `write` to force the cache clearing otherwise `return self.access_token` will return False
            self.sudo().write({'access_token': str(uuid.uuid4())})
        return self.access_token

    def _get_share_url(self, redirect=False, signup_partner=False, pid=None, share_token=True):
        """
        Build the url of the record  that will be sent by mail and adds additional parameters such as
        access_token to bypass the recipient's rights,
        signup_partner to allows the user to create easily an account,
        hash token to allow the user to be authenticated in the chatter of the record portal view, if applicable
        :param redirect : Send the redirect url instead of the direct portal share url
        :param signup_partner: allows the user to create an account with pre-filled fields.
        :param pid: = partner_id - when given, a hash is generated to allow the user to be authenticated
            in the portal chatter, if any in the target page,
            if the user is redirected to the portal instead of the backend.
        :return: the url of the record with access parameters, if any.
        """
        self.ensure_one()
        params = {
            'model': self._name,
            'res_id': self.id,
        }
        if share_token and hasattr(self, 'access_token'):
            params['access_token'] = self._portal_ensure_token()
        if pid:
            params['pid'] = pid
            params['hash'] = self._sign_token(pid)
        if signup_partner and hasattr(self, 'partner_id') and self.partner_id:
            params.update(self.partner_id.signup_get_auth_param()[self.partner_id.id])

        return '%s?%s' % ('/mail/view' if redirect else self.access_url, url_encode(params))

    def _notify_get_groups(self, msg_vals=None):
        access_token = self._portal_ensure_token()
        groups = super(PortalMixin, self)._notify_get_groups(msg_vals=msg_vals)
        local_msg_vals = dict(msg_vals or {})

        if access_token and 'partner_id' in self._fields and self['partner_id']:
            customer = self['partner_id']
            local_msg_vals['access_token'] = self.access_token
            local_msg_vals.update(customer.signup_get_auth_param()[customer.id])
            access_link = self._notify_get_action_link('view', **local_msg_vals)

            new_group = [
                ('portal_customer', lambda pdata: pdata['id'] == customer.id, {
                    'has_button_access': False,
                    'button_access': {
                        'url': access_link,
                    },
                    'notification_is_customer': True,
                })
            ]
        else:
            new_group = []
        return new_group + groups

    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to the online document for
        portal users or if force_website=True in the context. """
        self.ensure_one()

        user, record = self.env.user, self
        if access_uid:
            try:
                record.check_access_rights('read')
                record.check_access_rule("read")
            except exceptions.AccessError:
                return super(PortalMixin, self).get_access_action(access_uid)
            user = self.env['res.users'].sudo().browse(access_uid)
            record = self.with_user(user)
        if user.share or self.env.context.get('force_website'):
            try:
                record.check_access_rights('read')
                record.check_access_rule('read')
            except exceptions.AccessError:
                if self.env.context.get('force_website'):
                    return {
                        'type': 'ir.actions.act_url',
                        'url': record.access_url,
                        'target': 'self',
                        'res_id': record.id,
                    }
                else:
                    pass
            else:
                return {
                    'type': 'ir.actions.act_url',
                    'url': record._get_share_url(),
                    'target': 'self',
                    'res_id': record.id,
                }
        return super(PortalMixin, self).get_access_action(access_uid)

    @api.model
    def action_share(self):
        action = self.env["ir.actions.actions"]._for_xml_id("portal.portal_share_action")
        action['context'] = {'active_id': self.env.context['active_id'],
                             'active_model': self.env.context['active_model']}
        return action

    def get_portal_url(self, suffix=None, report_type=None, download=None, query_string=None, anchor=None):
        """
            Get a portal url for this model, including access_token.
            The associated route must handle the flags for them to have any effect.
            - suffix: string to append to the url, before the query string
            - report_type: report_type query string, often one of: html, pdf, text
            - download: set the download query string to true
            - query_string: additional query string
            - anchor: string to append after the anchor #
        """
        self.ensure_one()
        url = self.access_url + '%s?access_token=%s%s%s%s%s' % (
            suffix if suffix else '',
            self._portal_ensure_token(),
            '&report_type=%s' % report_type if report_type else '',
            '&download=true' if download else '',
            query_string if query_string else '',
            '#%s' % anchor if anchor else ''
        )
        return url
