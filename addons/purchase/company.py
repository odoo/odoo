# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models

class company(models.Model):
    _inherit = 'res.company'

    po_lead = fields.Float(string='Purchase Lead Time', required=True,\
        help="Margin of error for vendor lead times. When the system "
             "generates Purchase Orders for procuring products, "
             "they will be scheduled that many days earlier "
             "to cope with unexpected vendor delays.", default=1.0)

    po_double_validation = fields.Selection([
        ('one_step', 'Confirm purchase orders in one step'),
        ('two_step', 'Get 2 levels of approvals to confirm a purchase order')
        ], string="Levels of Approvals", default='one_step',\
        help="Provide a double validation mechanism for purchases")
    po_double_validation_amount = fields.Monetary(string='Double validation amount', default=5000,\
        help="Minimum amount for which a double validation is required")
