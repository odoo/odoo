# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class Company(models.Model):
    _inherit = "res.company"

    snailmail_color = fields.Boolean(string='Color', default=False)
    snailmail_duplex = fields.Boolean(string='Both sides', default=False)
    snailmail_send_by_letter = fields.Boolean(string='Send by Letter by default', default=True)
