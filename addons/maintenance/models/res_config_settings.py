# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import mail


class ResConfigSettings(mail.ResConfigSettings):

    module_maintenance_worksheet = fields.Boolean(string="Custom Maintenance Worksheets")
