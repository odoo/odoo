# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    "name": "Vietnam - Accounting",
    "version": "2.0",
    'category': 'Localization',
    "description": """
This is the module to manage electronic invoices for Vietnam in Odoo.
=========================================================================



""",
    "depends": [
        "l10n_vn",
    ],
    "data": [
        'security/security.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
    ],
    "auto_install": True,
}
