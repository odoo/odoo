# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class BarcodeRulePart(models.Model):
    _inherit = 'barcode.rule.part'

    type = fields.Selection(
        selection_add=[('coupon', 'Coupon')],
        ondelete={'coupon': 'set default'})
