{
    "name": """Chile - E-invoicing""",
    'version': '1.2',
    'category': 'Accounting/Localizations/EDI',
    'sequence': 12,
    'author':  'Blanco Martín & Asociados',
    'description': """
EDI Chilean Localization
========================
This module facilitates the generation of DTE (Electronic Taxable Document) for Chilean invoicing. Key features include:
- DTE Format in XML: The document is structured in XML format for standardized electronic transactions.
- Direct Communication with SII: Enables direct interaction with the Servicio de Impuestos Internos (SII) to send invoices and other tax documents related to sales.
- Customer Communication: Sends sales DTEs to customers.
- Supplier Communication: Accepts DTEs from suppliers (vendors).
- SII Notifications: Informs SII about the acceptance or rejection of vendor bills or other DTEs.

Note: To display barcodes on invoices, the `pdf417gen` library is required.

Electronic Receipts Compliance
==============================

As per SII requirements, starting March 2021, all boletas transactions must be sent to SII using a different web service than the one used for electronic invoices. Previously, only a daily report was required.

Recent Changes
==============

- Elimination of Daily Sales Book Requirement: As of August 1st, 2022, the daily sales book ("Libro de ventas diarias") is no longer required by the authorities and has been removed from this version of Odoo.

Differences between Electronic Boletas and Electronic Invoicing Workflows
=========================================================================

1. Dedicated Servers for Boletas:
- Production environment: `palena.sii.cl`
- Test environment: `maullin.sii.cl`

2. Different Authentication and Status Services:
- Authentication services and methods for querying delivery and document status differ between electronic boletas and electronic invoices.

3. Authentication Token:
- The process for obtaining authentication tokens varies.

4. Updated XML Schema:
- New tags have been incorporated into the XML schema for electronic boletas.

5. Validation Diagnosis:
- Electronic boletas receive validation diagnoses through a REST web service using the delivery track-id.
- Electronic invoices continue to receive diagnoses via email.

6. Track-ID Length:
- Electronic boletas: 15 digits
- Electronic invoices: 10 digits

For detailed guidance, refer to the [SII Guide](https://www.sii.cl/factura_electronica/factura_mercado/Instructivo_Emision_Boleta_Elect.pdf).

    """,
    'website': 'http://www.bmya.cl',
    'depends': [
        'l10n_cl',
        'account_edi',
        'account_debit_note',
        'certificate',
    ],
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
