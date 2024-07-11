# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hungary - E-invoicing',
    'version': '1.0.0',
    'category': 'Accounting/Localizations/EDI',
    'countries': ['hu'],
    'author': 'DO Tech (OdooTech Zrt.), BDSC Business Consulting Kft. & Odoo S.A.',
    'description': """
* Submit e-invoices to the NAV (Hungarian Tax Agency) as part of the invoicing process.
* Perform the Tax Audit Export (Adóhatósági Ellenőrzési Adatszolgáltatás) in NAV 3.0 format.
    """,
    'website': 'https://www.odootech.hu',
    'depends': ['account_debit_note', 'base_iban', 'l10n_hu'],
    'data': [
        'security/ir.model.access.csv',
        'data/uom.uom.csv',
        'data/account_cash_rounding.xml',
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
        'wizard/account_move_send_views.xml',
        'wizard/l10n_hu_edi_cancellation.xml',
        'wizard/l10n_hu_edi_tax_audit_export.xml',
    ],
    'demo': [
        'demo/demo_partner.xml',
    ],
    'post_init_hook': 'post_init',
    'auto_install': ['l10n_hu'],
    'license': 'LGPL-3',
}
