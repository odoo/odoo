# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """Inheriting ResConfigSettings to add fields and functions"""
    _inherit = 'res.config.settings'

    seller_approval = fields.Boolean(
        string='Seller Approval',
        help='Seller Approval',
        config_parameter='multi_vendor_marketplace.seller_approval')
    quantity_approval = fields.Boolean(
        string='Quantity Approval',
        help='Quantity Approval',
        config_parameter='multi_vendor_marketplace.quantity_approval')
    product_approval = fields.Boolean(
        string='Product Approval',
        help='Product Approval',
        config_parameter='multi_vendor_marketplace.product_approval')
    internal_categ_id = fields.Many2one(
        'product.category',
        required=True,
        string='Internal category',
        help='Internal category',
        config_parameter='multi_vendor_marketplace.internal_categ_id',
        default=lambda self: self.env.ref(
            'product.product_category_all'))
    product_variants = fields.Boolean(
        string='Product variants',
        help='Product variants',
        config_parameter='multi_vendor_marketplace.product_variants')

    @api.onchange('product_variants')
    def _onchange_product_variants(self):
        """Changing the product variants settings"""
        for data in self.env['product.template'].search([]):
            data.product_variants_setting = self.product_variants
    product_pricing = fields.Boolean(
        string='Product Price',
        help='Product Price',
        config_parameter='multi_vendor_marketplace.product_pricing')

    @api.onchange('product_pricing')
    def _onchange_product_pricing(self):
        """Changing the product price settings"""
        for data in self.env['product.template'].search([]):
            data.product_price_setting = self.product_pricing
    uom = fields.Boolean(string='UOM', help='Units of Measurement',
                         config_parameter='multi_vendor_marketplace.uom')

    @api.onchange('uom')
    def _onchange_uom(self):
        """Changing product uom"""
        for data in self.env['product.template'].search([]):
            data.product_uom = self.uom
    seller_location_id = fields.Many2one(
        'stock.location',
        string='Location', required=True,
        help='Location',
        config_parameter='multi_vendor_marketplace.seller_location_id',
        default=lambda self: self.env.ref(
            'stock.stock_location_stock'))
    seller_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse', help='Warehouse',
        required=True,
        config_parameter='multi_vendor_marketplace.seller_warehouse_id',
        default=lambda self: self.env.ref(
            'stock.warehouse0'))
    seller_shop = fields.Boolean(
        string='Seller shop', help='Seller shop',
        config_parameter='multi_vendor_marketplace.seller_shop')
    commission = fields.Float(
        string='Seller shop', help='Seller shop',
        default=2,
        config_parameter='multi_vendor_marketplace.commission')
    currency = fields.Many2one(
        'res.currency',
        string='Marketplace Currency',
        help='Marketplace Currency',
        config_parameter='multi_vendor_marketplace.currency',
        required=True, default=lambda self: self.env.company.currency_id)
    amt_limit = fields.Integer(
        string='Amount limit', help='Amount limit',
        config_parameter='multi_vendor_marketplace.amt_limit')
    min_gap = fields.Integer(
        string='Minimum Gap', help='Minimum Gap',
        config_parameter='multi_vendor_marketplace.min_gap',
        default='2')
    pay_journal = fields.Many2one(
        'account.journal',
        string='Seller Payment Journal',
        help='Seller Payment Journal',
        config_parameter='multi_vendor_marketplace.pay_journal',
        default=lambda self: self.env.ref(
            'multi_vendor_marketplace.seller_payment_journal_creation'))
    pay_product = fields.Many2one(
        'product.product',
        string='Payment Product',
        help='Payment Product',
        config_parameter='multi_vendor_marketplace.pay_product',
        default=lambda self: self.env.ref(
            'multi_vendor_marketplace.seller_payment_product_creation'))
    seller_request_admin_mail = fields.Boolean(
        string='Mail notification',
        help='Enable notification for '
             'Admin',
        config_parameter='multi_vendor_marketplace.seller_request_admin_mail')
    seller_request_admin_mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        help='Email Template',
        config_parameter=
        'multi_vendor_marketplace.seller_request_admin_mail_template_id',
        default=lambda self: self.env['ir.model.data']._xmlid_to_res_id(
            'multi_vendor_marketplace.seller_request_admin_mail_template'),
        required=True)
    seller_request_seller_mail = fields.Boolean(
        string='Seller notification', help='Enable notification for Seller',
        config_parameter='multi_vendor_marketplace.seller_request_seller_mail')
    seller_request_seller_mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        help='Email template',
        config_parameter=
        'multi_vendor_marketplace.seller_request_seller_mail_template_id',
        default=lambda self: self.env['ir.model.data']._xmlid_to_res_id(
            'multi_vendor_marketplace.seller_request_seller_mail_template'),
        required=True, )
    seller_approve_admin_mail = fields.Boolean(
        string='Admin notification',
        help='Enable notification for Admin',
        config_parameter='multi_vendor_marketplace.seller_approve_admin_mail')
    seller_approve_admin_mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template', help='Email template',
        config_parameter=
        'multi_vendor_marketplace.seller_approve_admin_mail_template_id',
        default=lambda self: self.env['ir.model.data']._xmlid_to_res_id(
            'multi_vendor_marketplace.seller_state_admin_mail_template'),
        required=True)
    seller_approve_seller_mail = fields.Boolean(
        'Enable notification for Seller',
        config_parameter='multi_vendor_marketplace.seller_approve_seller_mail')
    seller_approve_seller_mail_template_id = fields.Many2one(
        'mail.template', string='Email Template',
        help='Email Template',
        config_parameter=
        'multi_vendor_marketplace.seller_approve_seller_mail_template_id',
        default=lambda self: self.env['ir.model.data']._xmlid_to_res_id(
            'multi_vendor_marketplace.seller_state_seller_mail_template'),
        required=True)
    product_approve_admin_mail = fields.Boolean(
        string='Admin Notification', help='Enable notification for Admin',
        config_parameter='multi_vendor_marketplace.product_approve_admin_mail')
    product_approve_admin_mail_template_id = fields.Many2one(
        'mail.template', 'Email Template',
        config_parameter=
        'multi_vendor_marketplace.product_approve_admin_mail_template_id',
        default=lambda self: self.env['ir.model.data']._xmlid_to_res_id(
            'multi_vendor_marketplace.product_state_admin_mail_template'),
        required=True)
    product_approve_seller_mail = fields.Boolean(
        'Enable notification for Seller',
        config_parameter='multi_vendor_marketplace.product_approve_seller_mail')
    product_approve_seller_mail_template_id = fields.Many2one(
        'mail.template', 'Email Template',
        config_parameter=
        'multi_vendor_marketplace.product_approve_seller_mail_template_id',
        default=lambda self: self.env['ir.model.data']._xmlid_to_res_id(
            'multi_vendor_marketplace.product_state_seller_mail_template'),
        required=True)
    new_order_seller_mail = fields.Boolean(
        'Enable notification for Seller',
        config_parameter='multi_vendor_marketplace.new_order_admin_mail')
    new_order_seller_mail_template_id = fields.Many2one(
        'mail.template', 'Email Template',
        config_parameter=
        'multi_vendor_marketplace.new_order_admin_mail_template_id',
        default=lambda self: self.env['ir.model.data']._xmlid_to_res_id(
            'multi_vendor_marketplace.new_order_seller_mail_template'),
        required=True)
    prod_count = fields.Boolean('Product Count',
                                config_parameter=
                                'multi_vendor_marketplace.prod_count')
    sale_count = fields.Boolean(
        config_parameter='multi_vendor_marketplace.sale_count')
    seller_addr = fields.Boolean('Seller Address',
                                 config_parameter=
                                 'multi_vendor_marketplace.seller_addr')
    seller_since = fields.Boolean(
        config_parameter='multi_vendor_marketplace.seller_since')
    ret_policy = fields.Boolean('Return Policy',
                                config_parameter=
                                'multi_vendor_marketplace.ret_policy')
    ship_policy = fields.Boolean('Shipping Policy',
                                 config_parameter=
                                 'multi_vendor_marketplace.ship_policy')
    shop_tnc = fields.Boolean('Seller Shop Terms & Conditions',
                              config_parameter=
                              'multi_vendor_marketplace.shop_tnc')
    contact_seller_button = fields.Boolean(
        'Contact Seller Button',
        config_parameter='multi_vendor_marketplace.contact_seller_button')
    bcome_seller = fields.Boolean('Become a Seller Button',
                                  config_parameter=
                                  'multi_vendor_marketplace.bcome_seller')
    recent_products = fields.Integer('Recently Added Products',
                                     config_parameter=
                                     'multi_vendor_marketplace.recent_products')
    show_seller_review = fields.Boolean(
        config_parameter=
        'multi_vendor_marketplace.show_seller_review')
    auto_publish_seller_review = fields.Boolean(
        config_parameter=
        'multi_vendor_marketplace.auto_publish_seller_review')
    seller_review_count = fields.Integer(
        'Display Seller Reviews',
        config_parameter=
        'multi_vendor_marketplace.seller_review_count')
    show_sell_menu_header = fields.Boolean(
        'Sell Menu on Header',
        config_parameter=
        'multi_vendor_marketplace.show_sell_menu_header')
    show_sell_menu_footer = fields.Boolean(
        'Sell Menu on Footer',
        config_parameter=
        'multi_vendor_marketplace.show_sell_menu_footer')
    show_sellers_list = fields.Boolean(
        'Sellers List',
        config_parameter=
        'multi_vendor_marketplace.show_sellers_list')
    sell_link_label = fields.Char(
        config_parameter=
        'multi_vendor_marketplace.sell_link_label')
    seller_list_link_label = fields.Char(
        config_parameter=
        'multi_vendor_marketplace.seller_list_link_label')
    seller_shop_list_link_label = fields.Char(
        config_parameter=
        'multi_vendor_marketplace.seller_shop_list_link_label')
    new_status_msg = fields.Text('For New Satus', )
    pending_status_msg = fields.Text('For Pending Satus')
    image = fields.Binary('Landing page banner',
                          related='website_id.seller_banner',
                          readonly=False)
    show_t_and_c = fields.Boolean('Marketplace Terms and Conditions',
                                  config_parameter=
                                  'multi_vendor_marketplace.show_t_and_c')

    def set_values(self):
        """Supering the function to set the values"""
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('res.config.settings.new_status_msg', self.new_status_msg)
        set_param('res.config.settings.pending_status_msg',
                  self.pending_status_msg)
        set_param('res.config.settings.pay_journal', self.pay_journal)

    @api.model
    def get_values(self):
        """Supering the function to get the values"""
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res['new_status_msg'] = get_param('res.config.settings.new_status_msg')
        res['pending_status_msg'] = get_param(
            'res.config.settings.pending_status_msg')
        res['pay_journal'] = get_param('res.config.settings.pay_journal')
        return res
