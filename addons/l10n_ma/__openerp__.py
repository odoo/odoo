# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2010 kazacube (http://kazacube.com).

{
    'name': 'Maroc - Accounting',
    'version': '1.0',
    'author': 'kazacube',
    'category': 'Localization/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Maroc.
=================================================================

Ce Module charge le modèle du plan de comptes standard Marocain et permet de
générer les états comptables aux normes marocaines (Bilan, CPC (comptes de
produits et charges), balance générale à 6 colonnes, Grand livre cumulatif...).
L'intégration comptable a été validé avec l'aide du Cabinet d'expertise comptable
Seddik au cours du troisième trimestre 2010.""",
    'website': 'http://www.kazacube.com',
    'depends': ['base', 'account'],
    'data': [
        'account_pcg_morocco.xml',
        'l10n_ma_tax.xml',
        'account_chart_template.yml',
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
}
