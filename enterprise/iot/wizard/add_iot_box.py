# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
import random
import requests
import time

from odoo import _, api, fields, models
from odoo.exceptions import UserError

TIMEOUT = 20


class AddIotBox(models.TransientModel):
    _name = 'add.iot.box'
    _description = 'Add IoT Box wizard'

    def _default_token(self):
        web_base_url = self.get_base_url()
        token = str(random.randint(1000000000, 9999999999))
        iot_token = self.env['ir.config_parameter'].sudo().search([('key', '=', 'iot_token')], limit=1)
        if iot_token:
            # token valable 60 minutes
            if iot_token.write_date + timedelta(minutes=60) > fields.datetime.now():
                token = iot_token.value
            else:
                iot_token.write({'value': token})
        else:
            self.env['ir.config_parameter'].sudo().create({'key': 'iot_token', 'value': token})
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid', default='')
        enterprise_code = self.env['ir.config_parameter'].sudo().get_param('database.enterprise_code', default='')
        return web_base_url + '?token=' + token + '&db_uuid=' + db_uuid + '&enterprise_code=' + enterprise_code

    token = fields.Char(string='Token', default=_default_token, store=False)
    pairing_code = fields.Char(string='Pairing Code')

    def box_pairing(self):
        if not self.pairing_code:
            raise UserError(_("Please enter a pairing code."))

        data = {
            'params': {
                'pairing_code': (self.pairing_code or '').upper().strip(),
                'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                'database_url': self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                'enterprise_code': self.env['ir.config_parameter'].sudo().get_param('database.enterprise_code'),
                'token': self.env['ir.config_parameter'].sudo().get_param('iot_token'),
            },
        }
        try:
            req = requests.post('https://iot-proxy.odoo.com/odoo-enterprise/iot/connect-db', json=data, timeout=TIMEOUT)
        except requests.exceptions.ReadTimeout:
            raise UserError(_("We had troubles pairing your IoT Box. Please try again later."))

        response = req.json()

        if 'error' in response:
            if response['error']['code'] == 404:
                raise UserError(_(
                    "The pairing code you provided was not found in our system. Please check that you "
                    "entered it correctly."
                ))
            else:
                raise requests.exceptions.ConnectionError()
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'info',
                    'message': _("Using Pairing Code to connect..."),
                    'sticky': False,
                    'params': {
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                },
            }

    # TODO: Dead code to remove
    # Since https://github.com/odoo/enterprise/pull/68394 we don't need to reload the page anymore
    # For clients that did not upgrade, we keep this method as their old views still call it
    def reload_page(self):
        return self.env["ir.actions.actions"]._for_xml_id("iot.iot_box_action")
