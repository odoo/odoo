# Part of TNPD Prison Management System.
# License: LGPL-3

{
    'name': 'Prison Jail Master',
    'version': '19.0.1.0.0',
    'category': 'Prison Management',
    'summary': 'Hierarchical master data for Tamil Nadu prison jails',
    'description': """
Prison Jail Master
==================
Three-tier hierarchy enforced at the ORM level:

    Central Jail  →  District Jail  →  Sub Jail

Features
--------
* ``prison.jail`` model with parent-child hierarchy and SQL constraints
* Stored computed ``central_jail_id`` for fast cross-level filtering
* Tree, Form, and Search views with per-type filters and group-by
* REST APIs: list central jails, filter districts by central, filter sub-jails by district
* Integration base for the Employee and Transfer modules
    """,
    'author': 'TNPD',
    'website': '',
    'license': 'LGPL-3',

    'depends': ['base', 'hr'],

    'data': [
        'security/ir.model.access.csv',
        'views/prison_jail_views.xml',
        'views/menu_items.xml',
        'data/prison_jail_data.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
