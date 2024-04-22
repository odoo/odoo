# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Italy - Declaration of Intent',
    'version': '0.1',
    'depends': [
        'l10n_it_edi',
        'sale',
    ],
    'description': """
    Add support for the Declaration of Intent (Dichiarazione di Intento) to the Italian localization.
    """,
    'category': 'Accounting/Localizations',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations/italy.html',
    'data': [
        'security/ir.model.access.csv',
        'data/account_tax_template.xml',
        'data/account_fiscal_position_template_data.xml',
        'data/invoice_it_template.xml',
        'views/l10n_it_edi_doi_declaration_of_intent_views.xml',
        'views/account_move_views.xml',
        'views/report_invoice.xml',
        'views/res_partner_views.xml',
        'views/sale_ir_actions_report_templates.xml',
        'views/sale_order_views.xml',
    ],
    'license': 'LGPL-3',
    'post_init_hook': '_l10n_it_edi_doi_post_init',
}
