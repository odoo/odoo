# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    pad_server = fields.Char(related='company_id.pad_server', string="Pad Server *")
    pad_key = fields.Char(related='company_id.pad_key', string="Pad Api Key *")
