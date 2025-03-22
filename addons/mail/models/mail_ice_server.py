# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.mail.tools.credentials import get_twilio_credentials
import logging
import requests

_logger = logging.getLogger(__name__)

class MailIceServer(models.Model):
    _name = 'mail.ice.server'
    _description = 'ICE server'

    server_type = fields.Selection([('stun', 'stun:'), ('turn', 'turn:')], string='Type', required=True, default='stun')
    uri = fields.Char('URI', required=True)
    username = fields.Char()
    credential = fields.Char()

    def _get_local_ice_servers(self):
        """
        :return: List of up to 5 dict, each of which representing a stun or turn server
        """
        # firefox has a hard cap of 5 ice servers
        ice_servers = self.sudo().search([], limit=5)
        formatted_ice_servers = []
        for ice_server in ice_servers:
            formatted_ice_server = {
                'urls': '%s:%s' % (ice_server.server_type, ice_server.uri),
            }
            if ice_server.username:
                formatted_ice_server['username'] = ice_server.username
            if ice_server.credential:
                formatted_ice_server['credential'] = ice_server.credential
            formatted_ice_servers.append(formatted_ice_server)
        return formatted_ice_servers

    def _get_ice_servers(self):
        """
        :return: List of dict, each of which representing a stun or turn server,
                formatted as expected by the specifications of RTCConfiguration.iceServers
        """
        if self.env['ir.config_parameter'].sudo().get_param('mail.use_twilio_rtc_servers'):
            (account_sid, auth_token) = get_twilio_credentials(self.env)
            if account_sid and auth_token:
                url = f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Tokens.json'
                response = requests.post(url, auth=(account_sid, auth_token), timeout=60)
                if response.ok:
                    response_content = response.json()
                    if response_content:
                        return response_content['ice_servers']
                else:
                    _logger.warning(f"Failed to obtain TURN servers, status code: {response.status_code}, content: {response.content}.")
        return self._get_local_ice_servers()
