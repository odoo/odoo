# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import models, fields, api, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    money_in_out = fields.Boolean("Money In/Out")
    money_in_out_receipt = fields.Boolean("Money In/Out Receipt")

    # Wallet field
    enable_wallet = fields.Boolean('Wallet')
    wallet_product = fields.Many2one('product.product', string="Wallet Product")
    wallet_account_id = fields.Many2one("account.account", string="Wallet Account")
    wallet_payment_method_id = fields.Many2one("pos.payment.method", "Wallet Payment Method")

    # Gift Card field
    enable_gift_card = fields.Boolean('Gift Card')
    gift_card_account_id = fields.Many2one('account.account', string="Gift Card Account")
    gift_card_product_id = fields.Many2one('product.product', string="Gift Card Product")
    enable_journal_id = fields.Many2one('pos.payment.method', string="Enable Journal")
    manual_card_number = fields.Boolean('Manual Card No.')
    default_exp_date = fields.Integer('Default Card Expire Months')
    msg_before_card_pay = fields.Boolean('Confirm Message Before Card Payment')

    # default Customer
    enable_default_customer = fields.Boolean('Default Customer')
    default_customer_id = fields.Many2one('res.partner', string="Select Customer")

    # Gift voucher field
    enable_gift_voucher = fields.Boolean('Gift Voucher')
    gift_voucher_account_id = fields.Many2one("account.account", string="Account")
    gift_voucher_journal_id = fields.Many2one("pos.payment.method", string="Payment Method")

    # warehouse
    show_warehouse_qty = fields.Boolean(string='Display Warehouse Quantity')

    # Internal Stock Transfer
    enable_int_trans_stock = fields.Boolean(string="Internal Stock Transfer")

    # Select sale person from POS
    enable_select_sale_person = fields.Boolean(string="Select Sale Person")

    # Bag Charges
    enable_bag_charges = fields.Boolean(string="Bag Charges")

    # Multi UOM
    enable_multi_uom = fields.Boolean(string="Multi UOM")

    # Lock Screen
    enable_manual_lock = fields.Boolean(string="Manual")
    enable_automatic_lock = fields.Boolean(string="Automatic")
    time_interval = fields.Float(string="Time Interval (Minutes)")

    # Customer History
    is_customer_purchase_history = fields.Boolean(string='Customer History')

    # loyalty fields
    enable_loyalty = fields.Boolean('Loyalty', related='show_loyalty_field')
    show_loyalty_field = fields.Boolean('Show', compute='show_enable_loyalty_field')
    loyalty_payment_method_id = fields.Many2one("pos.payment.method", "Loyalty Payment Method")

    # vertical-category
    enable_vertical_category = fields.Boolean('Vertical Product Category')

    # return_order
    enable_pos_return = fields.Boolean("Order Return from POS")

    # POS session close
    enable_close_session = fields.Boolean(string="Enable Close Session")
    z_report_pdf = fields.Boolean(string="Z Report Pdf")
    email_close_session_report = fields.Boolean(string="Email Z Report")
    allow_with_zero_amount = fields.Boolean(string="Allow With 0 Amount")
    email_template_id = fields.Many2one('mail.template', string="Email Template")
    users_ids = fields.Many2many('res.users', string="Users")

    # enable_signature
    enable_signature = fields.Boolean('Enable Signature')

    # product summary report
    enable_product_summary = fields.Boolean(string="Product Summary Report")
    product_current_month_date = fields.Boolean(string="Product Current Month Date")
    product_summary_signature = fields.Boolean(string="Signature")

    # order summary report
    enable_order_summary = fields.Boolean(string='Order Summary Report')
    order_current_month_date = fields.Boolean(string="Order Current Month Date")
    order_signature = fields.Boolean(string="Order Signature")

    # payment summary report
    enable_payment_summary = fields.Boolean(string="Payment Summary Report")
    payment_current_month_date = fields.Boolean(string="Payment Current Month Date")

    # audit report
    enable_audit_report = fields.Boolean("Print Audit Report")

    # Customer screen
    customer_display = fields.Boolean("Customer Display")
    image_interval = fields.Integer("Image Interval", default=10)
    customer_display_details_ids = fields.One2many('customer.display', 'config_id', string="Customer Display Details")
    ad_video_ids = fields.One2many('ad.video', 'config_id', string="Advertise Video Id (YouTube)")
    enable_customer_rating = fields.Boolean("Customer Display Rating")
    set_customer = fields.Boolean("Set Customer")
    create_customer = fields.Boolean("Create Customer")

    # product screen
    enable_product_screen = fields.Boolean("Product Screen")

    # pos serial
    enable_pos_serial = fields.Boolean("Enable POS serials")
    restrict_lot_serial = fields.Boolean("Restrict Lot/Serial Quantity")
    product_exp_days = fields.Integer("Product Expiry Days", default="0")

    # Order and line note
    enable_order_note = fields.Boolean('Order Note')
    enable_product_note = fields.Boolean('Product / Line Note')
    is_ordernote_receipt = fields.Boolean('Order Note on Receipt')
    is_productnote_receipt = fields.Boolean('Product / Line Note on Receipt')

    # Alternative Product
    enable_optional_product = fields.Boolean("Alternative Product")

    # Cross Selling
    enable_cross_selling = fields.Boolean("Cross Selling")

    # Active Ingredients
    enable_active_ingredients = fields.Boolean("Active Ingredients")
    display_ingredients_in_orderline = fields.Boolean("Display in OrderLine")

    # Delivery charges
    enable_delivery_charges = fields.Boolean("Active Delivery Charge")
    delivery_product_id = fields.Many2one('product.product', string="Delivery Product")
    delivery_product_amount = fields.Float(string="Delivery Charge Amount")

    # Material Monitor
    enable_material_monitor = fields.Boolean("Material Monitor")
    enable_stock_location = fields.Boolean("Stock Location", compute='show_enable_material_monitor')

    # POS Promotion
    enable_pos_promotion = fields.Boolean("POS Promotion")

    def show_enable_material_monitor(self):
        if self.env.user.has_group('stock.group_stock_multi_locations'):
            self.enable_stock_location = True
        else:
            self.enable_stock_location = False

    def show_enable_loyalty_field(self):
        if self.env['ir.config_parameter'].sudo().get_param('flexipharmacy.enable_loyalty'):
            self.show_loyalty_field = True
        else:
            self.show_loyalty_field = False

    @api.constrains('time_interval')
    def _check_time_interval(self):
        if self.enable_automatic_lock and self.time_interval < 0:
            raise Warning(_('Time Interval Not Valid'))

    @api.onchange('cash_control')
    def _onchange_enable_wallet(self):
        if not self.cash_control and self.money_in_out:
            self.money_in_out = False
        if not self.cash_control and self.enable_wallet:
            self.enable_wallet = False


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def get_html_report(self, id, report_name):
        report = self._get_report_from_name(report_name)
        document = report._render_qweb_html(id, data={})
        if document:
            return document
        return False
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
