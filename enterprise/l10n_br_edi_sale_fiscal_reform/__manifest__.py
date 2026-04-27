# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Avatax Brazil Sale Fiscal Reform',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['l10n_br_edi_sale', 'l10n_br_avatax_sale', 'l10n_br_edi_fiscal_reform'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}
