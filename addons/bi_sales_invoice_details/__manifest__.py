# -*- coding : utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
	'name'			: 'Invoice Details on Sales order',
	'version'		: '16.0.0.1',
	'category'		: 'Sales',
	'license'		: 'OPL-1',
	'summary'		: 'You can see Invoiced Amount, Invoice Amount Due, Invoice Paid Amount in sale order',
	'description'	: """You can see Invoiced Amount, Invoice Amount Due, Invoice Paid Amount in sale order. 
	Invoiced Amount Details For Sale Order
	Invoice Amount Details For Sale
	Sale invoice details
	Sale order invoice details
	Sale invoiced details
	Sale invoice details
	invoice amount on Sale order
	invoice amount details on Sale order
	invoice details for Sale order
	invoice detail for Sale order
	invoice detail on Sales
	invoice detail in Sale order
	invoice amount details on Sales order

	""",
	'author'		: 'Browseinfo',
	'website'		: 'https://www.browseinfo.in',
	'depends'		: ['base','sale','sale_management','stock'],
	'data'			: [
	                    'views/sales_invoice_views.xml'
						],
	'installable'	: True,
	'auto_install'	: False,
	'live_test_url':'https://youtu.be/kjFQSg5URcw',
	"images":['static/description/Banner.gif'],
}
