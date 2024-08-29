# -*- coding: utf-8 -*-
from odoo.addons import base
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel, base.ResConfigSettings):

    web_app_name = fields.Char('Web App Name', config_parameter='web.web_app_name')
