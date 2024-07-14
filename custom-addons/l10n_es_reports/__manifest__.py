# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2008-2010 Zikzakmedia S.L. (http://zikzakmedia.com) All Rights Reserved.
#                         Jordi Esteve <jesteve@zikzakmedia.com>
# Copyright (c) 2012-2013, Grupo OPENTIA (<http://opentia.com>) Registered EU Trademark.
#                         Dpto. Consultoría <consultoria@opentia.es>
# Copyright (c) 2013 Serv. Tecnol. Avanzados (http://www.serviciosbaeza.com)
#                    Pedro Manuel Baeza <pedro.baeza@serviciosbaeza.com>


{
    'name': 'Spain - Accounting (PGCE 2008) Reports',
    'countries': ['es'],
    'version': '4.1',
    'author': 'Spanish Localization Team',
    'website': 'https://launchpad.net/openerp-spain',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting reports for Spain
    """,
    'depends': [
        'l10n_es', 'account_reports',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_invoice_views.xml',
        'views/res_company_views.xml',
        'data/pymes_profit_and_loss_report_data.xml',
        'data/pymes_balance_sheet_report_data.xml',
        'data/full_balance_sheet_report_data.xml',
        'data/assoc_balance_sheet_report_data.xml',
        'data/account_libros_registro_de_iva_export.xml',
        'data/account_report_ec_sales_list_report.xml',
        'data/account_tags.xml',
        'data/mod111.xml',
        'data/mod115.xml',
        'data/mod303.xml',
        'data/mod347.xml',
        'data/mod349.xml',
        'data/mod390.xml',
        'wizard/aeat_boe_export_wizards.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_es', 'account_reports'],
    'license': 'OEEL-1',
}
