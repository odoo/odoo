# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Inter Company Module for Sale/Purchase Orders (with Inventory link)',
    'version': '1.1',
    'summary': 'Intercompany SO/PO',
    'category': 'Productivity',
    'description': ''' Module for synchronization of Inventory Documents between several companies.
    For example, this allows you to have a delivery receipt created automatically in the receiving company when another company of the system confirms a delivery order.
''',
    'depends': [
        'sale_stock',
        'purchase_stock',
        'sale_purchase_inter_company_rules'
    ],
    'data': [
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
