# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Andorra - Accounting',
    'summary': ('Creació de grups comptables, Pla General Comptable'
                ' i taxes andorranes (IGI, IRPF)'),
    'version': '1.0',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ad'],
    'author': 'Batista10 <https://batista10.cat>',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations.html',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Andorra Comptes Comptables
==========================

    * Creació de grups comptables
    * Creació del Pla General Comptable
    * Creació de taxes andorranes (IGI, IRPF)
""",
    'depends': [
        'account',
        'base_iban',
        'base_vat',
    ],
    'data': [
        'data/res_partner_data.xml',
    ],
    'license': 'LGPL-3',
}
