# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import mail


class ResCompany(mail.ResCompany):

    snailmail_color = fields.Boolean(default=True)
    snailmail_cover = fields.Boolean(string='Add a Cover Page', default=False)
    snailmail_duplex = fields.Boolean(string='Both sides', default=False)
