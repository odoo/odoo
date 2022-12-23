# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Morocco - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ma'],
    'author': 'kazacube (http://www.kazacube.com)',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Morocco.
====================================================================

Ce Module charge le modèle du plan de comptes standard Marocain et permet de
générer les états comptables aux normes marocaines (Bilan, CPC (comptes de
produits et charges), balance générale à 6 colonnes, Grand livre cumulatif...).
L'intégration comptable a été validé avec l'aide du Cabinet d'expertise comptable
Seddik au cours du troisième trimestre 2010.""",
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'depends': [
        'base',
        'account',
    ],
    'data': [
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
