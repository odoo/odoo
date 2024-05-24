# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    def _default_confirmation_sms_picking_template(self):
        try:
            return self.env.ref('stock_sms.sms_template_data_stock_delivery').id
        except ValueError:
            return False

    stock_sms_confirmation_template_id = fields.Many2one(
        'sms.template', string="SMS Template",
        default=_default_confirmation_sms_picking_template,
        help="SMS sent to the customer once the order is delivered.")
