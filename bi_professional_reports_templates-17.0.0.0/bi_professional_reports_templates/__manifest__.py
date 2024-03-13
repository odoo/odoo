# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Odoo Professional Report Templates',
    'version': '17.0.0.0',
    'category': 'Tools',
    'license': 'OPL-1',
    'summary': 'Easily Customizable Report Template for Quotation/SO/Sales, Invoice, Picking/Delivery Order,RFQ/PO/Purchases',
    'description': """
		Customize report, customize pdf report, customize template report, Customize Sales Order report,Customize Purchase Order report, Customize invoice report, Customize delivery Order report, Accounting Reports, Easy reports, Flexible report,Fancy Report template.
		
    """,
    'license': 'OPL-1',
    'author': 'BrowseInfo',
    'live_test_url': 'https://youtu.be/_aihFWW4a5E',
    'website': 'https://www.browseinfo.com',
    'depends': ['base', 'account', 'sale', 'purchase', 'stock', 'sale_stock', 'base_vat', 'sale_management',
                'purchase_stock'],
    'data': [

        "views/res_company.xml",

        "invoice_report/fency_report_invoice.xml",
        "invoice_report/report_invoice_classic.xml",
        "invoice_report/report_invoice_modern.xml",
        "invoice_report/report_invoice_odoo_standard.xml",
        "delivery_report/fency_report_deliveryslip.xml",
        "delivery_report/modern_report_deliveryslip.xml",
        "delivery_report/odoo_standard_report_deliveryslip.xml",
        "delivery_report/report_deliveryslip_classic.xml",
        "purchase_report/classic_report_purchaseorder.xml",
        "purchase_report/classic_report_purchasequotation.xml",
        "purchase_report/fency_report_purchaseorder.xml",
        "purchase_report/fency_report_purchasequotation.xml",
        "purchase_report/modern_report_purchaseorder.xml",
        "purchase_report/modern_report_purchasequotation.xml",
        "purchase_report/odoo_standard_report_purchaseorder.xml",
        "purchase_report/odoo_standard_report_purchasequotation.xml",
        "sale_report/classic_report_saleorder.xml",
        "sale_report/fency_report_saleorder.xml",
        "sale_report/modern_report_saleorder.xml",
        "sale_report/odoo_standard_report_saleorder.xml",
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'live_test_url': 'https://youtu.be/_aihFWW4a5E',
    "images": ['static/description/Banner.gif'],
}
