# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Work Resource',
    'version': '2.0',
    'category': 'Hidden',
    'description': """
Module for work, time and resource management
=============================================

A resource represent something that can be scheduled (a developer on a task or a
work center on manufacturing orders). This module manages a resource calendar
associated to every resource. It also manages the leaves of every resource.
    """,
    'depends': ['base'],
    'data': [
        'data/work_resource_data.xml',
        'security/ir.model.access.csv',
        'security/work_resource_security.xml',
        'views/work_resource_views.xml',
        'views/res_company_views.xml',
    ],
    'demo': ['data/work_resource_demo.xml'],
}
