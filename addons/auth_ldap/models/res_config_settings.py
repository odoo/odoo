# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import base_setup


class ResConfigSettings(base_setup.ResConfigSettings):

    ldaps = fields.One2many(related='company_id.ldaps', string="LDAP Parameters", readonly=False)
