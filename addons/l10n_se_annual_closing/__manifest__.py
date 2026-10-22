# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Sweden - Annual Closing',
    'countries': ['se'],
    'author': 'XCLUDE, Odoo S.A.',
    'category': 'Accounting/Localizations',
    'description': """
Swedish annual closing
----------------------

- SNI industry codes on companies
- SRU mapping of the accounts for the income tax return (INK2, INK3, INK4, NE)
- F-tax approval stated on customer invoices
    """,
    'depends': [
        'l10n_se',
    ],
    'auto_install': True,
    'data': [
        'security/ir.access.csv',
        'data/l10n_se.sni.csv',
        'views/l10n_se_sni_views.xml',
        'views/l10n_se_sru_mapping_views.xml',
        'views/partner_view.xml',
        'views/res_config_settings_views.xml',
        'views/report_invoice_templates.xml',
    ],
    'other_files': [
        # SRU mapping templates, loaded on demand (Settings > Load SRU Mapping)
        'data/ink2_sru_template.csv',
        'data/ink3_sru_template.csv',
        'data/ink4_sru_template.csv',
        'data/ne_sru_template.csv',
    ],
    'license': 'LGPL-3',
}
