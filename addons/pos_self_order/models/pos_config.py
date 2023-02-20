# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PosConfig(models.Model):
    _inherit = 'pos.config'

    self_order_location = fields.Selection([
        ('table', 'Table'),
        ('kiosk', 'Kiosk')
        ],
        string='Order at', default='kiosk', readonly=False,
        help="Choose where the customer will order from")
    self_order_allow_open_tabs = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
        ],
        string='Pay After:', default='no', 
        help="Choose when the customer will pay")

    @api.constrains('self_order_location', 'self_order_allow_open_tabs')
    def _check_required_fields(self):
        if self.module_pos_self_order and not self.self_order_location:
            raise ValidationError(_('Please select the order location for self order'))
        if self.self_order_location == 'table' and not self.self_order_allow_open_tabs:
            raise ValidationError(_('Please select a value for "Pay After"'))
