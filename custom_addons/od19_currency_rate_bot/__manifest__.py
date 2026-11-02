{
    "name": "OD19 Currency Rate Bot (BOT Provider + Mini Bar)",
    "author": "Auto-Info, Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-thailand",
    "summary": "Bank of Thailand (BOT) official exchange rate provider with document mini bar and smart date fallback",
    "version": "19.0.1.0.0",
    "category": "Financial Management/Configuration",
    # The BOT provider is derived from currency_rate_update_TH_BOT (OCA/l10n-thailand)
    # which is licensed AGPL-3, therefore this module is AGPL-3.
    "license": "AGPL-3",
    "depends": ["currency_rate_update", "sale", "purchase"],
    "data": [
        "security/od19_currency_rate_bot_security.xml",
        "data/config_parameter.xml",
        "data/mini_bar_config_parameter.xml",
        "views/res_currency_views.xml",
        "views/res_currency_rate_provider.xml",
        "views/res_config_settings.xml",
        "views/mini_bar_account_move.xml",
        "views/mini_bar_account_payment.xml",
        "views/mini_bar_sale_order.xml",
        "views/mini_bar_purchase_order.xml",
    ],
    "installable": True,
    "application": False,
    "icon": "/od19_currency_rate_bot/static/description/icon.svg",
}
