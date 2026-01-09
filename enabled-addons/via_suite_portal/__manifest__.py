{
    'name': 'ViaSuite Portal',
    'version': '1.0.0',
    'category': 'Administration',
    'summary': 'Global Login Dispatcher and Tenant Management Portal',
    'description': """
ViaSuite Portal
===============
This module provides a central gateway for all ViaSuite tenants.

Main Features:
--------------
* **Global Dispatcher**: Automatically redirects users from the root domain (viafronteira.app) to their respective tenant subdomains based on Keycloak claims.
* **Tenant Management**: Central database for managing customer environments, subdomains, and status.
*   **Admin Dashboard**: Easy access to all client environments for support and administration.

*Note: This module should only be installed in the management database (e.g. via-suite-viafronteira). It should NOT be installed in the template database.*
    """,
    'author': 'ViaFronteira, LLC',
    'website': 'https://viafronteira.com',
    'depends': ['via_suite_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/tenant_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
