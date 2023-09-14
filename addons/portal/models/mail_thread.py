# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac

from functools import wraps
from inspect import Parameter, signature

from odoo import fields, models, _
from odoo.http import request
from odoo.addons.bus.websocket import wsrequest
from odoo.addons.portal.controllers.mail import _check_special_access


def check_portal_access_token(func):
    """ Decorate a function to extract the portal token from the request.
    The portal token is then available on the context of the current
    request.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        req = request or wsrequest
        portal_token = kwargs.pop("portal_token", None)
        portal_res_id = kwargs.pop("portal_res_id", None) or kwargs.get('thread_id')
        portal_res_model = kwargs.pop("portal_res_model", None) or kwargs.get('thread_model')
        if portal_token:
            record = request.env[portal_res_model].browse(int(portal_res_id)).sudo()
            has_access = _check_special_access(portal_res_model, int(portal_res_id), portal_token)
            if has_access:
                req.env.context = {**req.env.context, "portal_token": portal_token}
                if req.env.user._is_public() and hasattr(record, 'partner_id'):
                    req.env.context = {**req.env.context, "portal_partner": record.partner_id}
        return func(self, *args, **kwargs)

    old_sig = signature(wrapper)
    params = list(old_sig.parameters.values())
    new_param_index = next((
        index for index, param in enumerate(params)
        if param.kind in [Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD]
    ), len(params))
    for param in ["portal_token", "portal_res_id", "portal_res_model"]:
        new_param = Parameter(param, Parameter.POSITIONAL_OR_KEYWORD, default=None)
        params.insert(new_param_index, new_param)
        new_param_index += 1
    wrapper.__signature__ = old_sig.replace(parameters=params)
    return wrapper


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    _mail_post_token_field = 'access_token' # token field for external posts, to be overridden

    website_message_ids = fields.One2many('mail.message', 'res_id', string='Website Messages',
        domain=lambda self: [('model', '=', self._name), '|', ('message_type', '=', 'comment'), ('message_type', '=', 'email')], auto_join=True,
        help="Website communication history")

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        portal_enabled = isinstance(self, type(self.env['portal.mixin']))
        if not portal_enabled:
            return groups

        customer = self._mail_get_partners(introspect_fields=False)[self.id]
        if customer:
            access_token = self._portal_ensure_token()
            local_msg_vals = dict(msg_vals or {})
            local_msg_vals['access_token'] = access_token
            local_msg_vals['pid'] = customer.id
            local_msg_vals['hash'] = self._sign_token(customer.id)
            local_msg_vals.update(customer.signup_get_auth_param()[customer.id])
            access_link = self._notify_get_action_link('view', **local_msg_vals)

            new_group = [
                ('portal_customer', lambda pdata: pdata['id'] == customer.id, {
                    'active': True,
                    'button_access': {
                        'url': access_link,
                    },
                    'has_button_access': True,
                })
            ]
        else:
            new_group = []

        # enable portal users that should have access through portal (if not access rights
        # will do their duty)
        portal_group = next(group for group in groups if group[0] == 'portal')
        portal_group[2]['active'] = True
        portal_group[2]['has_button_access'] = True

        return new_group + groups

    def _sign_token(self, pid):
        """Generate a secure hash for this record with the email of the recipient with whom the record have been shared.

        This is used to determine who is opening the link
        to be able for the recipient to post messages on the document's portal view.

        :param str email:
            Email of the recipient that opened the link.
        """
        self.ensure_one()
        # check token field exists
        if self._mail_post_token_field not in self._fields:
            raise NotImplementedError(_(
                "Model %(model_name)s does not support token signature, as it does not have %(field_name)s field.",
                model_name=self._name,
                field_name=self._mail_post_token_field
            ))
        # sign token
        secret = self.env["ir.config_parameter"].sudo().get_param("database.secret")
        token = (self.env.cr.dbname, self[self._mail_post_token_field], pid)
        return hmac.new(secret.encode('utf-8'), repr(token).encode('utf-8'), hashlib.sha256).hexdigest()

    def _get_access_token_from_context(self):
        return self.env.context.get("portal_token")
