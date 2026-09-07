# -*- coding: utf-8 -*-
{
    'name': 'SIFNEXT Jurnal Besar',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Pusat Jurnal & Buku Besar Terintegrasi PPL dan Aset',
    'author': 'SIFNEXT',
    'depends': ['base'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/sif_coa_data.xml',
        'views/coa_views.xml',
        'views/jurnal_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}