# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Associations Management',
    'version': '0.1',
    'category': 'Marketing',
    'description': """
This module is to configure modules related to an association.
==============================================================

It installs the profile for associations to manage events, registrations, memberships, 
membership products (schemes).
    """,
    'depends': ['base_setup', 'membership', 'event'],
    'data': ['views/association_views.xml'],
    'installable': True,
    'license': 'LGPL-3',
}
