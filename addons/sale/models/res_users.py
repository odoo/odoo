# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    field_group_warning_sale = fields.Boolean(default=False,
                                               compute='_compute_groups', inverse='_compute_groups_inverse',
                                               group_xml_id='sale.group_warning_sale',
                                               string="A warning can be set on a product or a customer (Sale)")

    field_group_sale_layout = fields.Boolean(default=False,
                                               compute='_compute_groups', inverse='_compute_groups_inverse',
                                               group_xml_id='sale.group_sale_layout',
                                               string="Personalize sales order and invoice report")

    field_group_delivery_invoice_address = fields.Boolean(default=False,
                                               compute='_compute_groups', inverse='_compute_groups_inverse',
                                               group_xml_id='sale.group_delivery_invoice_address',
                                               string="Addresses in Sales Orders")

    field_group_show_price_subtotal = fields.Boolean(default=False,
                                               compute='_compute_groups', inverse='_compute_groups_inverse',
                                               group_xml_id='sale.group_show_price_subtotal',
                                               string="Show line subtotals without taxes (B2B)")

    field_group_show_price_total = fields.Boolean(default=False,
                                               compute='_compute_groups', inverse='_compute_groups_inverse',
                                               group_xml_id='sale.group_show_price_total',
                                               string="Show line subtotals with taxes included (B2C)")

    field_group_discount_per_so_line = fields.Boolean(default=False,
                                              compute='_compute_groups', inverse='_compute_groups_inverse',
                                              group_xml_id='sale.group_discount_per_so_line',
                                              string="Discount on lines")

    field_group_proforma_sales = fields.Boolean(default=False,
                                              compute='_compute_groups', inverse='_compute_groups_inverse',
                                              group_xml_id='sale.group_proforma_sales',
                                              string="Pro-forma Invoices")

    field_group_analytic_accounting = fields.Boolean(default=False,
                                              compute='_compute_groups', inverse='_compute_groups_inverse',
                                              group_xml_id='sale.group_analytic_accounting',
                                              string="Analytic Accounting for Sales")

    @api.onchange('field_group_warning_sale', 'field_group_sale_layout', 'field_group_delivery_invoice_address',
                  'field_group_show_price_subtotal', 'field_group_show_price_total', 'field_group_discount_per_so_line',
                  'field_group_proforma_sales', 'field_group_analytic_accounting')
    def _onchange_field_group_sales(self):
        res = self._onchange_field_group()
        return res
