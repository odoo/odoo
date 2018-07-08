# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo import api, fields, models, _


class PortalMixin(models.AbstractModel):
    _name = "portal.mixin"

    portal_url = fields.Char(
        'Portal Access URL', compute='_compute_portal_url',
        help='Customer Portal URL')

    @api.multi
    def _compute_portal_url(self):
        for record in self:
            record.portal_url = '#'

    def _get_access_token_field(self):
        """ Give the field used to fetch the customer portal access token, if
        any. Override this method if the field holding the token is named
        differently. """
        return 'access_token' if 'access_token' in self else False

    def _get_customer_field(self):
        """ Give the field used to fetch the customer partner_id, if any.
        Override this method if the field holding the token is named differently. """
        return 'partner_id' if 'partner_id' in self else False

    def _get_access_token(self):
        """ Get the current record access token """
        field = self._get_access_token_field()
        return self[field] if field else False

    def _get_customer(self):
        """ Get the current record custome (res.partner record) """
        field = self._get_customer_field()
        return self[field] if field else self.env['res.partner']

    def get_share_url(self):
        self.ensure_one()
        params = {
            'model': self._name,
            'res_id': self.id,
        }
        if hasattr(self, 'access_token') and self.access_token:
            params['access_token'] = self.access_token
        if hasattr(self, 'partner_id') and self.partner_id:
            params.update(self.partner_id.signup_get_auth_param()[self.partner_id.id])

        return '/mail/view?' + url_encode(params)

    @api.multi
    def _notify_get_groups(self, message, groups):
        access_token = self._get_access_token()
        customer = self._get_customer()

        if access_token and customer:
            additional_params = {
                'access_token': self.access_token,
            }
            additional_params.update(customer.signup_get_auth_param()[customer.id])
            access_link = self._notify_get_action_link('view', **additional_params)

            new_group = [
                ('portal_customer', lambda partner: partner.id == customer.id, {
                    'has_button_access': False,
                    'button_access': {
                        'url': access_link,
                        'title': ('View %s') % self.env['ir.model']._get(message.model).display_name,
                    },
                })
            ]
        else:
            new_group = []
        return super(PortalMixin, self)._notify_get_groups(message, new_group + groups)
