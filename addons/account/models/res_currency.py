# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import decimal_precision as dp


class CurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    rate = fields.Float(digits=dp.get_precision('Rate Precision'))
