# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - GSTR Document Summary',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'countries': ['in'],
    'summary': 'GSTR Document Summary Management',
    'description': "Functionality to manage GSTR Document Summary (Table 13) for India GST returns.",
    'depends': ['l10n_in_reports_gstr_spreadsheet'],
    'data': [
        'security/ir.model.access.csv',
        'views/gstr_document_summary_views.xml',
        'views/gst_return_period.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
