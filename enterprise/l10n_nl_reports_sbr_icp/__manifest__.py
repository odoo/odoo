# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Netherlands - SBR ICP',
    'version': '0.3',
    'category': 'Accounting/Localizations/SBR',
    'summary': 'EC Sales (ICP) SBR for Dutch localization',
    'description': """
SBR Dutch Localization
========================
Submit your Intracommunity Services to the Dutch tax authorities.
    """,
    'depends': [
        'l10n_nl_reports_sbr',
        'l10n_nl_intrastat',
    ],
    'external_dependencies': {
        'python': ['zeep'],
    },
    'data': [
        'report/l10n_nl_sbr_icp_template.xml',
        'security/ir.model.access.csv',
        'wizard/l10n_nl_sbr_icp_wizard_view.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
