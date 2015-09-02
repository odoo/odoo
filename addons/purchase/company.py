# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _

class company(models.Model):
    _inherit = 'res.company'
    po_lead = fields.Float(string='Purchase Lead Time', required=True,
        help="Margin of error for vendor lead times. When the system "\
             "generates Purchase Orders for procuring products, "\
             "they will be scheduled that many days earlier "\
             "to cope with unexpected vendor delays.", default=1.0)

