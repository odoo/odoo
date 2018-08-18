#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2013-2015 Akretion (http://www.akretion.com)

{
    'name': 'France - FEC',
    'category': 'Accounting',
    'summary': "Fichier d'Échange Informatisé (FEC) for France",
    'author': "Akretion,Odoo Community Association (OCA)",
    'depends': ['l10n_fr', 'account'],
    'data': [
        'wizard/account_fr_fec_view.xml',
    ],
    'auto_install': True,
}
