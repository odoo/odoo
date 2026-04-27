{
    'name': 'Italy - Tax Report XML Export',
    'countries': ['it'],
    'version': '0.1',
    'depends': [
        'account_reports',
        'l10n_it_edi',
    ],
    'description': """
Additional module to allow the export of the Italian monthly tax report to XML format.
    """,
    'category': 'Accounting/Localizations',
    'data': [
        'security/ir.model.access.csv',
        'data/tax_monthly_report_vat.xml',
        'data/tax_report_export_template.xml',
        'wizard/monthly_tax_report_xml_export_view.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
