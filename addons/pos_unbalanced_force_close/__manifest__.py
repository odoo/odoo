# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale Force Close Unbalanced Session',
    'version': '1.0.0',
    'category': 'Sales/Point Of Sale',
    'sequence': 20,
    'summary': 'Allow Force closing an unbalanced session.',
    'description': """
    This module allows closing unbalanced session by adding an account_move_line with the amount
    of the difference between credit and debit.
    Be carefull as this can cause discrepancies in your accounting.
    Use it on your own will.
    No support will be provided for unbalanced sessions closed with this module.
    """,
    'depends': ['point_of_sale'],
    'data': [
        'security/account_security.xml',
        'views/res_config_settings_view.xml',
        'views/pos_config_view.xml',
        'views/pos_session_view.xml',
        'wizard/confirmation_wizard.xml',
    ],
    'installable': True,
}
