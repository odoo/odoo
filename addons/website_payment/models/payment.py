# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class PaymentAcquirer(models.Model):
    _name = 'payment.acquirer'
    _inherit = ['payment.acquirer','website.published.mixin']
