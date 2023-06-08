# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class FiscalConfig(models.Model):
    _inherit = 'pos.config'

    fiscal_printer_ip = fields.Char(string='Fiscal Server IP', help="Local IP address of server an Fiscal receipt printer.")
