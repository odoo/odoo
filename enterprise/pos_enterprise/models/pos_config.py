# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    module_pos_iot = fields.Boolean('IoT Box', related="is_posbox")
    module_pos_urban_piper = fields.Boolean(string='Is an Urbanpiper')
