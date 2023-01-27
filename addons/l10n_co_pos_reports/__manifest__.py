# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Colombian - Point of Sale Details",
    'icon': '/l10n_co/static/description/icon.png',
    "version": "1.0",
    "description": """
Colombian - Point of Sale
=========================

    Extend POS Sales Details Report for Colombia
""",
    "category": "Localization",
    "auto_install": True,
    "depends": [
        "l10n_co_pos"
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/pos_details_view.xml",
        "views/pos_config_views.xml",
        "views/templates.xml",
    ],
    'license': 'LGPL-3',
}
