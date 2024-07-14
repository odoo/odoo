{
    "name": """Chile - E-invoicing""",
    'countries': ['cl'],
    'version': '1.1',
    'category': 'Accounting/Localizations',
    'sequence': 12,
    'author':  'Blanco Martín & Asociados',
    'description': """
EDI Chilean Localization
========================
This code allows to generate the DTE document for Chilean invoicing.
- DTE (Electronic Taxable Document) format in XML
- Direct Communication with SII (Servicio de Impuestos Internos) to send invoices and other tax documents related to sales.
- Communication with Customers to send sale DTEs.
- Communication with Suppliers (vendors) to accept DTEs from them.
- Direct Communication with SII informing the acceptance or rejection of vendor bills or other DTEs.

 In order to see the barcode on the invoice, you need the pdf417gen library.

    """,
    'website': 'http://www.bmya.cl',
    'depends': [
        'l10n_cl',
        'account_edi',
        'account_debit_note',
    ],
    'external_dependencies': {
        'python': [
            'zeep',
        ],
    },
    'data': [
        'views/account_journal_view.xml',
        'views/l10n_latam_document_type_view.xml',
        'views/dte_caf_view.xml',
        'views/fetchmail_server.xml',
        'views/report_invoice.xml',
        'views/account_move_view.xml',
        'views/account_payment_term_view.xml',
        'views/l10n_cl_certificate_view.xml',
        'views/res_config_settings_view.xml',
        'views/company_activities_view.xml',
        'views/res_company_view.xml',
        'views/res_partner_view.xml',
        'wizard/account_move_debit_note_view.xml',
        'wizard/account_move_reversal_view.xml',
        'template/ack_template.xml',
        'template/dd_template.xml',
        'template/dte_template.xml',
        'template/envio_dte_template.xml',
        'template/response_dte_template.xml',
        'template/signature_template.xml',
        'template/ted_template.xml',
        'template/token_template.xml',
        'data/mail_template_data.xml',
        'data/cron.xml',
        'data/l10n_cl.company.activities.csv',
        'data/sequence.xml',
        'security/ir.model.access.csv',
        'security/l10n_cl_edi_security.xml',
    ],
    'demo': [
        'demo/partner_demo.xml',
        'demo/edi_demo.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_cl'],
    'license': 'OEEL-1',
}
