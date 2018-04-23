# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    is_email = fields.Boolean('Email by default', default=True)
    is_print = fields.Boolean('Print by default', default=True)
