# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Accounting Reports',
    'version': '1.1',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting reports for Belgium
    """,
    'depends': [
        'l10n_be',
        'account_reports',
        'account_loans',
    ],
    'data': [
        'views/account_325_forms_views.xml',
        'wizard/l10n_be_325_form_wizard.xml',
        'views/l10n_be_vat_statement_views.xml',
        'views/l10n_be_wizard_xml_export_options_views.xml',
        'views/l10n_be_vendor_partner_views.xml',
        'views/res_partner_views.xml',
        'data/profit_and_loss_comp_a.xml',
        'data/profit_and_loss_comp_f.xml',
        'data/profit_and_loss_asso_a.xml',
        'data/profit_and_loss_asso_f.xml',
        'data/balance_sheet_comp_acon.xml',
        'data/balance_sheet_comp_acap.xml',
        'data/balance_sheet_comp_fcon.xml',
        'data/balance_sheet_comp_fcap.xml',
        'data/balance_sheet_asso_a.xml',
        'data/balance_sheet_asso_f.xml',
        'data/account_tag_data.xml',
        'data/account_report_ec_sales_list_report.xml',
        'data/tax_report.xml',
        'data/partner_vat_listing.xml',
        'security/ir.model.access.csv',
        'security/account_325_security_rules.xml',
        'report/l10n_be_281_50_pdf_templates.xml',
        'report/l10n_be_281_50_xml_templates.xml',
        'report/l10n_be_325_pdf_templates.xml',
    ],
    'installable': True,
    'post_init_hook': '_l10n_be_reports_post_init',
    'auto_install': ['l10n_be', 'account_reports'],
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'l10n_be_reports/static/src/components/**/*',
        ],
    },
}
