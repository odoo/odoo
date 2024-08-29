# -*- coding: utf-8 -*-
from odoo.addons import base
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel, base.ResConfigSettings):

    jitsi_server_domain = fields.Char(
        'Jitsi Server Domain',
        default='meet.jit.si',
        config_parameter='website_jitsi.jitsi_server_domain',
        help='The Jitsi server domain can be customized through the settings to use a different server than the default "meet.jit.si"')
