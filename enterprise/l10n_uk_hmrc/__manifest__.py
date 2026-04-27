{
    'name': 'UK - HMRC API',
    'countries': ['gb'],
    'author': 'Odoo',
    'version': '1.0',
    'category': 'Accounting/Localizations/UK/HMRC',
    'description': """
HMRC API for the United Kingdom
================================================
    """,
    'depends': [
        'l10n_uk',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/config_parameter.xml',
        'data/ir_cron.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/template_transaction_engine_base.xml',
        'views/template_transaction_engine_request.xml',
    ],
    'license': 'OEEL-1',
}
