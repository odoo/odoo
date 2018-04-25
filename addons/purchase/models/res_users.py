# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_manage_vendor_price = fields.Boolean(
        'Manage Vendor Price', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='purchase.group_manage_vendor_price')

    has_group_warning_purchase = fields.Boolean(
        'A warning can be set on a product or a customer (Purchase)',
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='purchase.group_warning_purchase')

    group_purchase_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_purchase_management'),
        string='Purchases', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_purchase_management')
