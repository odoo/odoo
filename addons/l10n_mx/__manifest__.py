# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#    Coded by: Alejandro Negrin anegrin@vauxoo.com,
#    Planified by: Alejandro Negrin, Humberto Arocha, Moises Lopez
#    Finance by: Vauxoo.
#    Audited by: Humberto Arocha (hbto@vauxoo.com) y Moises Lopez (moylop260@vauxoo.com)

{
    "name": "Mexico - Accounting",
    "version": "2.0",
    "author": "Vauxoo",
    'category': 'Localization',
    "description": """
Minimal accounting configuration for Mexico.
============================================

This Chart of account is a minimal proposal to be able to use OoB the
accounting feature of Odoo.

This doesn't pretend be all the localization for MX it is just the minimal
data required to start from 0 in mexican localization.

This modules and its content is updated frequently by openerp-mexico team.

With this module you will have:

 - Minimal chart of account tested in production environments.
 - Minimal chart of taxes, to comply with SAT_ requirements.

.. _SAT: http://www.sat.gob.mx/
    """,
    "depends": [
        "account",
    ],
    "data": [
        "data/account_tag_data.xml",
        "data/l10n_mx_chart_data.xml",
        "data/account.account.template.csv",
        "data/l10n_mx_chart_post_data.xml",
        "data/account_data.xml",
        "data/account_tax_data.xml",
        "data/fiscal_position_data.xml",
        "data/account_chart_template_data.xml",
        "data/res_bank_data.xml",
        "views/partner_view.xml",
        "views/res_bank_view.xml",
        "views/res_config_settings_views.xml",
        "views/account_views.xml",
    ],
}
