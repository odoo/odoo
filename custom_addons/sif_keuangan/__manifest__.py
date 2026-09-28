# -*- coding: utf-8 -*-
{
    'name': 'Accounting',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Pusat Jurnal & Buku Besar Terintegrasi PPL dan Aset',
    'author': 'SIFNEXT',
    'depends': ['base', 'web', 'hr'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/sif_coa_data.xml',
        'views/coa_views.xml',
        'views/jurnal_views.xml',
        'views/general_ledger_views.xml',
        'views/balance_sheet_views.xml',
        'views/profit_loss_views.xml',
        'views/menu_views.xml',
        'reports/general_ledger_report.xml',
        'reports/balance_sheet_report.xml',
        'reports/profit_loss_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sif_keuangan/static/src/reports_common.scss',
            'sif_keuangan/static/src/i18n.js',
            'sif_keuangan/static/src/general_ledger/**/*',
            'sif_keuangan/static/src/balance_sheet/**/*',
            'sif_keuangan/static/src/profit_loss/**/*',
        ],
    },


    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
