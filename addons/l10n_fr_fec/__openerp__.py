# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2013-2015 Akretion (http://www.akretion.com)

{
    'name': 'France - FEC',
    'version': '1.0',
    'category': 'French Localization',
    'license': 'AGPL-3',
    'summary': "Fichier d'Échange Informatisé (FEC) for France",
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com',
    'depends': ['l10n_fr', 'account_accountant'],
    'data': [
        'wizard/fec_view.xml',
    ],
    'installable': True,
    'auto_install': True,
}
