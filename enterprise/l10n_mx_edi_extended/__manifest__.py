# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'EDI for Mexico (Advanced Features)',
    'countries': ['mx'],
    'version': '0.1',
    'category': 'Hidden',
    'depends': [
        'l10n_mx_edi',
        'base_address_extended',
    ],
    'data': [
        'security/ir.model.access.csv',

        'data/4.0/cfdi.xml',
        'data/l10n_mx_edi.res.locality.csv',
        'data/l10n_mx_edi.tariff.fraction.csv',
        'data/product_data.xml',
        'data/res.city.csv',
        'data/uom_uom_data.xml',

        'views/l10n_mx_edi_tariff_fraction_view.xml',
        'views/account_journal_view.xml',
        'views/account_move_view.xml',
        'views/product_template_view.xml',
        'views/uom_uom_view.xml',
        'views/res_company_view.xml',
        'views/res_config_settings_view.xml',
        'views/res_partner_views.xml',
        'views/report_invoice.xml',

        'data/country.xml',
    ],
    'demo': [
        'demo/demo_cfdi.xml',
    ],
    'installable': True,
    'license': 'OEEL-1',
}
