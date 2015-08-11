# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    manufacturing_lead = fields.Float(string='Manufacturing Lead Time', required=True, default=1.0, help="Security days for each manufacturing operation.")
