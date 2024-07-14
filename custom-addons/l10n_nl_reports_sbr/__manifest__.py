# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Netherlands - SBR',
    'countries': ['nl'],
    'version': '0.3',
    'category': 'Accounting/Localizations/SBR',
    'summary': 'Dutch Localization for SBR documents',
    'description': """
SBR Dutch Localization
========================
Submit your Tax Reports to the Dutch tax authorities
    """,
    'depends': ['l10n_nl_reports'],
    'external_dependencies': {
        'python': ['xmlsec', 'zeep', 'cryptography'],
    },
    'data': [
        'report/l10n_nl_reports_sbr_tax_report_templates.xml',
        'security/ir.model.access.csv',
        'wizard/l10n_tax_report_sbr_views.xml',
        'views/res_config_settings_view.xml',
        'data/tax_report.xml',
    ],
    'installable': True,
    'license': 'OEEL-1',
}
