# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields
import requests
from hashlib import md5
import uuid
from datetime import timedelta

DEST_SERVER_URL = 'https://www.odoo.com'


class Users(models.Model):
    _inherit = 'res.users'

    referral_updates_last_fetch_time = fields.Datetime(description='The last time the referral updates were fetched from odoo.com')
    referral_updates_count = fields.Integer(default=0)

    @api.model
    def get_referral_updates_count_for_current_user(self):
        user = self.env.user
        last_fetch = user.referral_updates_last_fetch_time
        if not last_fetch or last_fetch <= fields.Datetime.now() - timedelta(days=1):
            payload = {
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
                'id': uuid.uuid4().hex,
            }
            result = requests.post(
                DEST_SERVER_URL + '/referral/notifications/' + user._get_referral_token(),
                json=payload,
                headers={'content-type': 'application/json'}).json()
            user.referral_updates_last_fetch_time = fields.Datetime.now()
            if 'result' in result and 'updates_count' in result['result']:
                user.referral_updates_count = result['result']['updates_count']
            else:
                user.referral_updates_count = 0
        return user.referral_updates_count

    def _get_referral_token(self):
        self.ensure_one()
        mail = self.partner_id.email
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        return md5((mail + dbuuid).encode('utf-8')).hexdigest()

    def _get_referral_link(self):
        self.ensure_one()
        return DEST_SERVER_URL + '/referral/register?token=' + self._get_referral_token() + '&referrer_email=' + self.partner_id.email
