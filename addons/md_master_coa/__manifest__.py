{
    'name': 'MD Portfolio — Master Chart of Accounts',
    'summary': 'Center-of-truth COA across all MD Portfolio companies, with QBO bridge scaffolding.',
    'description': """
Master Chart of Accounts for MD Portfolio
==========================================
* Single source of truth for account structure across all branches/companies.
* 345 standardised accounts (7 header + 338 detail) aligned with GAAP / IFRS.
* Kanban, list, form and dashboard views.
* Account-movement drill-down per master account (cross-company).
* Company↔Master mapping table (Phase 2: QBO 2-way sync).
    """,
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'author': 'MD Portfolio',
    'license': 'LGPL-3',
    'depends': ['account', 'mail', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'data/md_master_accounts_data.xml',
        'views/md_master_account_views.xml',
        'views/md_account_mapping_views.xml',
        'views/md_coa_manual_views.xml',
        'views/md_master_coa_menus.xml',
        'wizard/md_qbo_sync_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'md_master_coa/static/src/scss/md_master_coa.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
