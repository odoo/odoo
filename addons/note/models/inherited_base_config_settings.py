# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models

class BaseConfiguration(models.TransientModel):
    _inherit = 'base.config.settings'

    module_note_pad = fields.Boolean(string='Use collaborative pads (etherpad)')
