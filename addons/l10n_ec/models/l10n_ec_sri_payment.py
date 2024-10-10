# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10n_EcSriPayment(models.Model):

    _description = "SRI Payment Method"

    name = fields.Char("Name", translate=True)
    code = fields.Char("Code")
    active = fields.Boolean("Active", default=True)
