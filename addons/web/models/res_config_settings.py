# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import base


class ResConfigSettings(base.ResConfigSettings):

    web_app_name = fields.Char('Web App Name', config_parameter='web.web_app_name')
