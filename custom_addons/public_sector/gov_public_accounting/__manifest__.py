{
    "name": "AGI Gov - Public Accounting Bundle",
    "version": "19.0.1.0.0",
    "summary": "Meta-modulo contabil GOV que instala o pacote completo de contabilidade publica",
    "category": "Accounting/Accounting",
    "author": "AGI Gov",
    "license": "LGPL-3",
    "description": "Use este modulo para instalar o pacote contabil AGI Gov completo. "
                   "Para instalacao granular, instale os modulos gov_account_* separadamente.",
    "depends": [
        "gov_base",
        "gov_account_lock_date_update",
        "gov_account_move_template",
        "gov_account_spread_cost_revenue"
    ],
    "data": [
        "data/gov_public_accounting_group_bridge.xml",
        "views/res_company_views.xml"
    ],
    "installable": True,
    "application": False
}
