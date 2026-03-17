{
    'name': 'QBO Bridge',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Localization',
    'summary': 'Two-way sync bridge between QuickBooks Online and Kodoo',
    'description': """
        qbo_bridge
        ==========
        Bidirectional synchronisation between QuickBooks Online (QBO) and Kodoo (Odoo 19).

        Features
        --------
        * OAuth 2.0 live connection per QBO realm
        * File-import fallback: CSV, XLSX, JSON
        * Mixed multi-company layout: N Odoo companies ↔ M QBO realms
        * Entities: Chart of Accounts, Customers/Vendors, Invoices/Bills,
          Payments/Transactions, Journal Entries, Products/Items
        * Conflict detection and manual reconciliation UI
        * Full audit log per sync operation
        * Configurable cron schedule with per-mapping toggle
    """,
    'author': 'Kodoo',
    'website': 'https://kodoo.dev',
    'depends': [
        'account',
        'sale_management',
        'purchase',
        'product',
        'base_setup',
    ],
    'data': [
        'security/qbo_security.xml',
        'security/ir.model.access.csv',
        'data/qbo_cron.xml',
        'views/menu.xml',
        'views/qbo_realm_views.xml',
        'views/qbo_company_mapping_views.xml',
        'views/qbo_account_bridge_rule_views.xml',
        'views/qbo_conflict_views.xml',
        'views/qbo_sync_log_views.xml',
        'views/qbo_import_wizard_views.xml',
        'views/qbo_conflict_resolve_wizard_views.xml',
    ],
    'external_dependencies': {
        'python': ['requests', 'openpyxl'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
