# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_warning_sale = fields.Boolean(
        "A warning can be set on a product or a customer (Sale)",
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='sale.group_warning_sale')

    has_group_delivery_invoice_address = fields.Boolean(
        "Addresses in Sales Orders",
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='sale.group_delivery_invoice_address')

    has_group_discount_per_so_line = fields.Boolean(
        "Discount on lines",
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='sale.group_discount_per_so_line')

    has_group_proforma_sales = fields.Boolean(
        "Pro-forma Invoices",
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='sale.group_proforma_sales')

    has_group_sale_order_dates = fields.Boolean(
        "Sale Order Dates",
        compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='sale.group_sale_order_dates')
