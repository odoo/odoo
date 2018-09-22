# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from datetime import timedelta
import random
from odoo import api, fields, models
from odoo.exceptions import UserError

class AddIotBox(models.TransientModel):
    _name = 'add.iot.box'

    def _default_token(self):
        web_base_url = self.env['ir.config_parameter'].search([('key', '=', 'web.base.url')], limit=1)
        token = str(random.randint(1000000000, 9999999999))
        iot_token = self.env['ir.config_parameter'].search([('key', '=', 'iot_token')], limit=1)
        if iot_token:
            # token valable 60 minutes
            if iot_token.write_date + timedelta(minutes=60) > fields.datetime.now():
                token = iot_token.value
            else:
                iot_token.write({'value': token})
        else:
            self.env['ir.config_parameter'].create({'key': 'iot_token', 'value': token})
        return web_base_url.value + '|' + token

    token = fields.Char(string='Token', default=_default_token, store=False)

