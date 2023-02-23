# -*- coding: utf-8 -*-
{
    'name': 'Proxy features for account_edi',
    'description': """
This module adds generic features to register an Odoo DB on the proxy responsible for receiving data (via requests from web-services).
- An edi_proxy_user has a unique identification on a specific format (for example, the vat for Peppol) which
allows to identify him when receiving a document addressed to him. It is linked to a specific company on a specific
Odoo database.
- Encryption features allows to decrypt all the user's data when receiving it from the proxy.
- Authentication offers an additionnal level of security to avoid impersonification, in case someone gains to the user's database.
    """,
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['account_edi'],
    'external_dependencies': {
        'python': ['cryptography']
    },
    'data': [
        'security/ir.model.access.csv',
        'security/account_edi_proxy_client_security.xml',
        'views/account_edi_proxy_user_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
    'post_init_hook': '_create_demo_config_param',
}
