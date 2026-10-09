# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
	'name': "Product Image On Sale Order Line",
	'version': "16.0.0.3",
	'category': "Sales",
	'license':'OPL-1',
	'summary': "Display product image on sale order line print product image on sale order report print image on sale order line product image print product image on sale line product image in sale order line print Product image on sales order line",
	'description': """
	
			Display product image on sale order line. It will also display product image on sale order report. 
	
			Product Image On Sale Order Line in odoo,
			Sale report with product image in odoo,
			product image on sale order line and sale report in odoo,
			Identify product via image in odoo,
			Identify priduct via image on sale report in odoo,

	""",
	'author': "BrowseInfo",
	"website" : "https://www.browseinfo.com",
    'depends': ['base', 'sale_management'],
	'data': [
			'report/sale_order_report.xml',
			'views/view_sale_order.xml',
			],
	'currency': "EUR",
	'demo': [],
	'installable': True,
	'auto_install': False,
	'application': False,
	"live_test_url":'https://youtu.be/teAvEPOTNZw',
	"images":['static/description/Banner.gif'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
