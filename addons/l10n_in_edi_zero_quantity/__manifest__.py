# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
        "name": "Indian Accounting Zero Quantiy moveline",
        "version": "1.0",
        "icon": "/l10n_in/static/description/icon.png",
        "description": "Enables Add Zero Quantiy in account move line",
        "summary": "Enables Zero Quantiy for account move line in Indian EDI request to government",
        'data': [
            'views/account_move_views.xml',
        ],
        "depends": ['l10n_in_edi'],
        "license": "LGPL-3"
}
