# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    captured = fields.Boolean(help='True if this payment was successfully captured.')
