# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from datetime import timedelta
import random
from odoo import api, fields, models
from odoo.exceptions import UserError

class AddIotBox(models.TransientModel):
    _name = 'add.iot.box'

    token = fields.Char(string='Token', readonly=True)
    view_token = fields.Char(string='View token', compute='_get_token')

    @api.depends('token')
    def _get_token(self):

        web_base_url = self.env['ir.config_parameter'].search([('key', '=', 'web.base.url')], limit=1)
        token = str(random.randint(1000000000,9999999999))
        iot_token = self.env['ir.config_parameter'].search([('key', '=', 'iot_token')], limit=1)
        
        if iot_token:
            # token valable 60 minutes
            if iot_token.write_date + timedelta(minutes=60) > fields.datetime.now():
                token = iot_token.value
            else:
                iot_token.write({'value' : token,})
        else:
            iot_token = self.env['ir.config_parameter'].create({'key': 'iot_token',
                                                'value': token
                                                })

        self.token = web_base_url.value + '|' + token

