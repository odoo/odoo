# -*- coding: utf-8 -*-
# License: OPL-1
from odoo import api, fields, models, _

class PosConfig(models.Model):
    _inherit = "pos.config"

    barcode_scan_with_camera = fields.Boolean(
        'Scan with Camera',
        help='Please made sure your odoo hosting on domain with SSL (https)\n'
             'Allow scan any barcode viva camera of users used POS Session\n'
             'Allow scan barcode of clients, products ....'
    )

