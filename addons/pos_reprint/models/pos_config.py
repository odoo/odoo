# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_reprint = fields.Boolean(
        string='Receipt Reprinting', help="This allows you to reprint a previously printed receipt.")
