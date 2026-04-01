# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Brazil - Sale',
    'version': '1.0',
    'description': 'Sale modifications for Brazil',
    'category': 'Sales/Sales',
    'depends': [
        'l10n_br',
        'sale',
    ],
    'data': [
        'views/sale_portal_templates.xml',
        'report/sale_order_templates.xml',
        'report/report_invoice_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
