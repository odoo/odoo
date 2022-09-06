# -*- coding: utf-8 -*-
{
    'name': "Factur-X",
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
Factur-X module
===========================

Note that you need to activate PDF A in order to be able to submit a Factur-X pdf on Chorus Pro: 
go to Settings > Technical (debug mode) > System Parameters > select/create one with Key: edi.use_pdfa, Value: true.
With this setting, Chorus Pro will automatically detect the "PDF/A-3 (Factur-X)" format.
    """,
    'depends': ['account'],
    'data': [
        'data/facturx_data.xml',
        'data/facturx_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
