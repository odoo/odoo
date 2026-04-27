# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet document for GSTR1 Report",
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Spreadsheet document for GSTR1 Report',
    'description': 'Spreadsheet document for GSTR1 Report',
    'depends': ['documents_spreadsheet', 'l10n_in_reports_gstr'],
    'data': [
        "views/gst_return_period.xml",
    ],
    'installable': True,
    'auto_install': ['l10n_in_reports_gstr'],
    'license': 'OEEL-1',
}
