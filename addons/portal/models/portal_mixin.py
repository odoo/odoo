# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo import api, fields, models


class PortalMixin(models.AbstractModel):
    _name = "portal.mixin"

    portal_url = fields.Char(
        'Portal Access URL', compute='_compute_portal_url',
        help='Customer Portal URL')

    @api.multi
    def _compute_portal_url(self):
        for record in self:
            record.portal_url = '#'

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
