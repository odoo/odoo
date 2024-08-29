# -*- coding: utf-8 -*-
from odoo.addons import barcodes
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class BarcodeRule(models.Model, barcodes.BarcodeRule):

    type = fields.Selection(selection_add=[('coupon', 'Coupon')], ondelete={'coupon': 'set default'})
