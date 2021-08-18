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


class ResUsers(models.Model):
    _inherit = 'res.users'

    access_money_in_out = fields.Boolean('Money In/Out', default=True)
    access_wallet = fields.Boolean('Use Wallet', default=True)
    access_gift_card = fields.Boolean('Gift Card', default=True)
    access_default_customer = fields.Boolean('Default Customer', default=True)
    access_gift_voucher = fields.Boolean('Gift Voucher', default=True)
    access_warehouse_qty = fields.Boolean('Display Warehouse Quantity', default=True)
    access_int_trans_stock = fields.Boolean('Internal Stock Transfer', default=True)
    access_select_sale_person = fields.Boolean('Select Sale Person', default=True)
    access_bag_charges = fields.Boolean('Bag Charges', default=True)
    access_multi_uom = fields.Boolean('Multi UOM', default=True)
    access_pos_lock = fields.Boolean('POS Lock', default=True)
    access_purchase_history = fields.Boolean('Customer History', default=True)
    access_vertical_category = fields.Boolean('Vertical Product Category', default=True)
    access_pos_return = fields.Boolean('Order Return from POS', default=True)
    access_close_session = fields.Boolean('Enable Close Session', default=True)
    access_signature = fields.Boolean('Enable Signature', default=True)
    access_product_summary = fields.Boolean('Product Summary Report', default=True)
    access_order_summary = fields.Boolean('Order Summary Report', default=True)
    access_payment_summary = fields.Boolean('Payment Summary Report', default=True)
    access_audit_report = fields.Boolean('Print Audit Report', default=True)
    access_purchase_order = fields.Boolean('Product Screen', default=True)
    access_pos_order_note = fields.Boolean('Order Note', default=True)
    access_cross_selling = fields.Boolean('Cross Selling', default=True)
    access_alternative_product = fields.Boolean('Alternative Product', default=True)
    access_delivery_charges = fields.Boolean('Delivery Charges', default=True)
    access_material_monitor = fields.Boolean('Material Monitor', default=True)
    access_pos_promotion = fields.Boolean('POS Promotion', default=True)

    # POS Session Close
    display_amount_during_close_session = fields.Boolean("Display Amount During Close Session")
    pin = fields.Char("PIN Code")

    # POS Direct Login
    is_pos_direct_login = fields.Boolean('Pos Direct Login')
    default_pos_id = fields.Many2one('pos.config', string="POS Config")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
