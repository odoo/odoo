# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Get from ocn service when any device registered.
    ocn_token = fields.Char('OCN Token', copy=False, readonly=True, help='Used for sending notification to registered devices')
