# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import mail


class ResConfigSettings(mail.ResConfigSettings):

    microsoft_outlook_client_identifier = fields.Char('Outlook Client Id', config_parameter='microsoft_outlook_client_id')
    microsoft_outlook_client_secret = fields.Char('Outlook Client Secret', config_parameter='microsoft_outlook_client_secret')
