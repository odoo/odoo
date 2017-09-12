# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'France - Accounting - Certified CGI 286 I-3 bis',
    'version': '1.0',
    'category': 'Localization',
    'description': """Ce module permet à Odoo d'être en conformité avec les exigences d'inaltérabilité, de sécurisation et d'archivage des données de vente aux non assujettis à la TVA.
                      Pour les entreprises françaises opérant ce type de ventes, ce module doit être installé avant le 01/01/2018.
                      Une fois ce module installé, il ne doit un aucun cas être désinstallé.

""",
    'depends': ['l10n_fr'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'data': [
        'views/no_cancel.xml',
        'data/account_move.xml',
    ],
    'post_init_hook': '_setup_inalterability',
}
