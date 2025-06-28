# -*- coding: utf-8 -*-
{
    'name': "Italy - Stock DDT",
    'countries': ['it'],
    'website': 'https://www.odoo.com',
    'category': 'Accounting/Localizations/EDI',
    'version': '0.1',
    'description': """
Documento di Trasporto (DDT)

Whenever goods are transferred between A and B, the DDT serves
as a legitimation e.g. when the police would stop you.

When you want to print an outgoing picking in an Italian company,
it will print you the DDT instead.  It is like the delivery
slip, but it also contains the value of the product,
the transportation reason, the carrier, ... which make it a DDT.

We also use a separate sequence for the DDT as the number should not
have any gaps and should only be applied at the moment the goods are sent.

When invoices are related to their sale order and the sale order with the
delivery, the system will automatically calculate the linked DDTs for every
invoice line to export in the FatturaPA XML.
    """,
    'depends': ['l10n_it_edi', 'stock_delivery', 'stock_account'],
    'data': [
        'report/l10n_it_ddt_report.xml',
        'views/stock_picking_views.xml',
        'views/account_invoice_views.xml',
        'data/l10n_it_ddt_template.xml',
    ],
    'auto_install': True,
    'post_init_hook': '_create_picking_seq',
    'license': 'LGPL-3',
}
