# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Portugal - Accounting (Certification)',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This bridge module adds the technical requirements of the Portuguese Certification regulation (Administrative Decree no. 363/2010) that stipulates certain criteria concerning the inalterability and authenticity of invoicing data.
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

The module adds the following features:

- AT Series: allows the creation of document series, under which documents must be emitted.
- Digital signature: documents are signed after they are emitted. After being signed, key data cannot be modified.
- QR Code: a QR Code is added to signed documents
- Hash integrity report is available based on the digital signature
    """,
    'depends': ['l10n_pt'],
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'security/l10n_pt_security.xml',
        'report/l10n_pt_hash_integrity_templates.xml',
        'wizard/account_move_reversal_views.xml',
        'wizard/account_payment_register_views.xml',
        'wizard/l10n_pt_cancel_wizard_views.xml',
        'wizard/l10n_pt_reprint_reason_views.xml',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/account_tax_views.xml',
        'views/l10n_pt_at_series_views.xml',
        'views/report_invoice.xml',
        'views/report_payment_receipt_templates.xml',
        'views/report_template.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/ir_config_parameter_data.xml',
        'demo/l10n_pt_at_series_demo.xml',
    ],
    'post_init_hook': '_post_init_hook',
    'license': 'LGPL-3',
}
