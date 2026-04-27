# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Luxembourg - Accounting Reports',
    'version': '1.0',
    'description': """
Accounting reports for Luxembourg
=================================
Luxembourgish SAF-T (also known as FAIA) is standard file format for exporting various types of accounting transactional data using the XML format.
The first version of the SAF-T Financial is limited to the general ledger level including customer and supplier transactions.
Necessary master data is also included.
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_lu', 'account_asset', 'account_reports', 'account_saft'],
    'data': [
        'data/account_financial_html_report_pl.xml',
        'data/account_financial_html_report_pl_abr.xml',
        'data/account_financial_html_report_bs.xml',
        'data/account_financial_html_report_bs_abr.xml',
        'views/l10n_lu_yearly_tax_report_appendix_views.xml',
        'data/annual_tax_report/section_1.xml',
        'data/annual_tax_report/sections_345.xml',
        'data/annual_tax_report/section_6_appendix_a.xml',
        'data/annual_tax_report/section_7_appendix_bc.xml',
        'data/annual_tax_report/section_8_appendix_d.xml',
        'data/annual_tax_report/section_9_appendix_e.xml',
        'data/annual_tax_report/section_10_appendix_fg.xml',
        'data/annual_tax_report/section_11_appendix_opex.xml',
        'data/annual_tax_report/annual_tax_report.xml',
        'data/tax_report.xml',
        'data/saft_report.xml',
        'data/ec_sales_list_report.xml',
        'views/account_ec_sales_xml_template.xml',
        'views/electronic_report_template.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/l10n_lu_stored_sales_report_views.xml',
        'wizard/l10n_lu_generate_accounts_report.xml',
        'wizard/l10n_lu_generate_sales_report.xml',
        'security/ir.model.access.csv',
        'security/l10n_lu_yearly_tax_report_appendix_security.xml',
    ],
    'demo': ['demo/demo_company.xml'],
    'post_init_hook': '_l10n_lu_reports_post_init',
    'auto_install': ['l10n_lu', 'account_reports'],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'l10n_lu_reports/static/src/components/**/*',
        ],
    }
}
