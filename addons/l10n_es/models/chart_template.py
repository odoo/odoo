# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, api, models


class AccountTaxRepartitionLineTemplate(models.Model):
    _inherit = "account.tax.repartition.line.template"

    factor_percent = fields.Float(string="%", default=100, required=True, help="Factor to apply on the account move lines generated from this distribution line, in percents")
