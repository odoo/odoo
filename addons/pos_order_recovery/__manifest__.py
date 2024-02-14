# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': "PoS Order Recovery",
    'summary': "Allows to create PoS orders on received PoS orders that failed to syncronize",
    'description': """
        When a PoS order is validated, it is sent to the server which will attempt to create a PoS order in the backend.
        If the creation process failed for any reason, the PoS wil create by default an attachment file with the received content.
        This module allows to recover the failed PoS orders and create them in the backend from the PoS session.
    """,
    'category': 'Sales/Point of Sale',
    'version': '1.0',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/pos_session_smart_button.xml',
    ],
    'license': 'LGPL-3',
    'post_init_hook': '_generate_capture_record_from_existing_capture_attachments',
}
