# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_sale_order_template = fields.Boolean(
        "Quotation Templates",
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='sale_management.group_sale_order_template')
