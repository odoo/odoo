# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    # move this start + change from stock.X to product_expiry.X
    has_group_expiration_date_on_delivery_slip = fields.Boolean(
        'Display Expiration Dates on Delivery Slip',
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='product_expiry.group_expiration_date_on_delivery_slip')
    #move this end