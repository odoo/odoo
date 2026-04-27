# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Ecuadorian Accounting EDI",
    "version": "1.3",
    "description": """
EDI Ecuadorian Localization
===========================
Adds electronic documents with its XML, RIDE, with electronic signature and direct connection to tax authority SRI,

The supported documents are Invoices, Credit Notes, Debit Notes, Purchase Liquidations, Purchase Reimbursements and Withholds

Includes automations to easily predict the withholding tax to be applied to each purchase invoice
""",
    "author": "TRESCLOUD",
    "category": "Accounting/Localizations/EDI",
    "license": "OPL-1",
    "depends": [
        "account_edi",
        "certificate",
        "l10n_ec",
    ],
    "data": [
        "data/templates/edi_document.xml",
        "data/templates/edi_authorization.xml",
        "data/templates/edi_signature.xml",
        "data/l10n_ec.taxpayer.type.csv",
        "data/account.edi.format.csv",
        "data/res.country.csv",

        "security/ir.model.access.csv",
        "security/security.xml",

        "views/account_journal_view.xml",
        "views/account_move_views.xml",
        "views/l10n_ec_reimbursement_views.xml",
        "views/account_tax_view.xml",
        "views/product_view.xml",
        "views/l10n_ec_taxpayer_type_view.xml",
        "views/l10n_ec_edi_certificate_views.xml",
        "views/report_invoice.xml",
        "views/report_withhold.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_view.xml",
        "views/res_country_view.xml",

        'wizard/l10n_ec_wizard_account_withhold_view.xml',

        "data/mail_template_data.xml",
    ],
    'demo': [
        "demo/demo_company.xml",
        "demo/demo_partner.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_ec_edi/static/src/components/**/*',
        ],
    },
    "installable": True,
    "auto_install": ["l10n_ec"],
    'post_init_hook': '_post_install_hook_configure_ecuadorian_data',
}
