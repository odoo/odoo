# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class BarcodeRule(models.Model):
    _inherit = 'barcode.rule'

    type = fields.Selection(selection_add=[('coupon', 'Coupon')], ondelete={'coupon': 'set default'})
