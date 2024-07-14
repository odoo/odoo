# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
  'name': "eBay Connector",

  'summary': "Publish your products on eBay",

  'description': """
Publish your products on eBay
=============================

The eBay integrator gives you the opportunity to manage your Odoo's products on eBay.

Key Features
------------
* Publish products on eBay
* Revise, relist, end items on eBay
* Integration with the stock moves
* Automatic creation of sales order and invoices

  """,

  # Categories can be used to filter modules in modules listing
  # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/data/ir_module_category_data.xml
  # for the full list
  'category': 'Sales/Sales',
  'sequence': 325,
  'version': '1.0',
  'application': True,

  # any module necessary for this one to work correctly
  'depends': ['base', 'sale_management', 'stock_delivery', 'attachment_indexation'],
  'external_dependencies': {'python': ['ebaysdk']},

  # always loaded
  'data': [
      'security/ir.model.access.csv',
      'security/sale_ebay_security.xml',
      'wizard/ebay_link_listing_views.xml',
      'views/product_views.xml',
      'views/res_currency_views.xml',
      'views/res_country_views.xml',
      'views/res_config_settings_views.xml',
      'views/res_partner_views.xml',
      'views/stock_picking_views.xml',
      'data/ir_cron_data.xml',
      'data/sale_ebay_data.xml',
      'data/product_data.xml',
      'data/mail_activity_type_data.xml',
  ],
  'license': 'OEEL-1',
  'uninstall_hook': 'uninstall_hook',
}
