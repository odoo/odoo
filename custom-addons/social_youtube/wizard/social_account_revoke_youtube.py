# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests

from werkzeug.urls import url_encode

from odoo import fields, models, _
from odoo.exceptions import UserError


class SocialAccountYoutubeRevoke(models.TransientModel):
    """Wizard to revoke a Youtube access token linked to a social account."""
    _name = 'social.account.revoke.youtube'
    _description = 'Revoke YouTube Account'

    _YOUTUBE_REVOKE_URL = 'https://oauth2.googleapis.com/revoke'

    account_id = fields.Many2one('social.account', 'Account', required=True,
                                 readonly=True, ondelete='cascade')

    def action_revoke(self):
        self.ensure_one()

        params = {'token': self.account_id.youtube_access_token}
        response = requests.post(
            f'{self._YOUTUBE_REVOKE_URL}?{url_encode(params)}',
            timeout=10,
        )

        if not response.ok:
            try:
                error = response.json()['error']
            except Exception:
                error = _('Unknown')
            raise UserError(_('Could not revoke your account.\nError: %s', error))

        self.account_id.unlink()

        action = self.env['ir.actions.actions']._for_xml_id('social.action_social_account')
        action.update({
            'context': {'no_breadcrumbs': True},
            'target': 'main',
            'views': [(False, 'list')],
        })

        return action
