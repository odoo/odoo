# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hungary - E-invoicing',
    'category': 'Accounting/Localizations/EDI',
    'author': 'DO Tech (OdooTech Zrt.), BDSC Business Consulting Kft. & Odoo S.A.',
    'description': """
* Electronically report invoices to the NAV (Hungarian Tax Agency) when issuing physical (paper) invoices.
* Electronically receive vendor bills from the NAV.
* Perform the Tax Audit Export (Adóhatósági Ellenőrzési Adatszolgáltatás) in NAV 3.0 format.
* NAV Documentation: https://onlineszamla.nav.gov.hu/files/container/download/2025.10.09.%20EN_Online%20Invoice%20System%203.0%20Interface%20Specification%20.pdf
    """,
    'website': 'https://www.odootech.hu',
    'depends': ['account_debit_note', 'l10n_hu'],
    'data': [
        'data/uom.uom.csv',
        'data/template_requests.xml',
        'data/template_invoice.xml',
        'data/ir_cron.xml',
        'views/report_templates.xml',
        'views/report_invoice.xml',
        'views/account_move_views.xml',
        'views/product_template_views.xml',
        'views/account_tax_views.xml',
        'views/uom_uom_views.xml',
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/l10n_hu_edi_cancellation.xml',
        'wizard/l10n_hu_edi_receive_bills_wizard_views.xml',
        'wizard/l10n_hu_edi_tax_audit_export.xml',
        'security/ir.access.csv',
    ],
    'demo': [
        'demo/demo_partner.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_hu_edi/static/src/views/**/*',
        ],
    },
    'auto_install': ['l10n_hu'],
    'license': 'LGPL-3',
}
