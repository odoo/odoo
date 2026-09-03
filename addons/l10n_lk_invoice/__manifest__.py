# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Sri Lanka - Tax Invoice",
    "icon": "/account/static/description/l10n.png",
    "summary": "Sri Lanka tax invoice sequence format and report layout.",
    "description": """
Sri Lanka Tax Invoice
=====================
- Custom tax invoice sequence format: YYMMM_QQQQ_XXXXX
- Tax Invoice / Supply Date / Mode of Payment in PDF report
- VAT registration tracking for companies and partners
    """,
    "category": "Accounting/Localizations",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html",
    "depends": [
        "l10n_lk",
    ],
    "version": "1.0",
    "author": "Odoo S.A.",
    "installable": True,
    "auto_install": ["l10n_lk"],
    "data": [
        "views/report_invoice.xml",
        "views/res_partner_views.xml",
        "views/res_company_views.xml",
    ],
    "license": "LGPL-3",
}
