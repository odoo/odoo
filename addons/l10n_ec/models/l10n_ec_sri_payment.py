# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SriPayment(models.Model):

    _name = "l10n_ec.sri.payment"
    _description = "SRI Payment Method"
    _order = 'active DESC, sequence, id'

    sequence = fields.Integer(default=10)
    code = fields.Char("Code")
    name = fields.Char("Name")
    active = fields.Boolean(default=True)
