{
    'name': 'Spain - Facturae EDI - Administrative Centers Patch',
    'version': '1.0',
    'description': """
    Patch module to fix the missing Administrative Centers in the Facturae EDI.
    """,
    'license': 'LGPL-3',
    'category': 'Accounting/Localizations/EDI',
    'depends': [
        'l10n_es_edi_facturae',
    ],
    'data': [
        'data/l10n_es_edi_facturae_adm_centers.ac_role_type.csv',
        'data/facturae_templates.xml',

        'security/ir.model.access.csv',

        'views/res_partner_views.xml',
    ],
    'demo': [
        'demo/l10n_es_edi_facturae_demo.xml',
    ],
    'auto_install': True,
}
