# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SriPayment(models.Model):

    _name = "l10n.ec.sri.payment"

    name = fields.Char("Name")
    code = fields.Char("Code")
