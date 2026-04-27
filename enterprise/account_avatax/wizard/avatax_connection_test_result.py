# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AvataxConnectionTestResult(models.TransientModel):
    _name = "avatax.connection.test.result"
    _description = 'Test connection with avatax'

    server_response = fields.Html(string='Server Response')
