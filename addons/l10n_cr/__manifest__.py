{
    'name': 'Costa Rica - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['cr'],
    'url': 'https://github.com/CLEARCORP/odoo-costa-rica',
    'author': 'ClearCorp S.A.',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Costa Rica - Accounting
=======================

Base localization module for Costa Rica. Electronic invoicing is delivered separately by l10n_cr_edi.

* Chart of accounts on a 6-digit numeric scheme
  (1 Activo / 2 Pasivo / 3 Patrimonio / 4 Ingresos / 5 Costos y Gastos).
* IVA taxes covering every CodigoTarifaIVA of Anexos y Estructuras v4.4, the transitional rates
  used only on credit and debit notes ship archived.
* 2% income tax withholding applied by State entities.
* Fiscal positions: Domestic, State institutions, Foreign (export) and Free Trade Zone.
* Identification types: Cédula Física, Cédula Jurídica, DIMEX, NITE and No Contribuyente.
* Document types for the ten Hacienda comprobantes; invoice, credit note and debit note are active.
* Address data: 84 cantones and 492 distritos on top of the seven provinces provided by base.
    """,
    'depends': [
        'account',
        'account_debit_note',
        'base_address_extended',
        'contacts',
        'l10n_latam_invoice_document',
    ],
    'auto_install': ['account'],
    'data': [
        'views/res_partner_views.xml',
        'data/res_country_data.xml',
        'data/l10n_latam.document.type.csv',
        'data/res.city.csv',
        'data/l10n_cr.res.city.district.csv',
        'views/portal_address_templates.xml',
        'views/res_city_views.xml',
        'views/res_city_district_views.xml',
        'views/res_company_views.xml',
        'security/ir.access.csv',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_cr/static/src/interactions/**/*',
        ],
    },
    'demo': [
        'demo/demo_partner.xml',
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
