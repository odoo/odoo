# -*- coding: utf-8 -*-
{
    'name' : 'Fleet Management',
    'version' : '0.1',
    'depends' : [
        'base',
        'hr',
    ],
    'demo': ['demo.xml'],
    'author' : 'OpenERP S.A.',
    'description' : """
    I'm a good module and I will handle the cars of your company !
    """,
    'installable' : True,
    'application' : True,
    'data' : [
        'fleet_view.xml',
    ],
    'update_xml' : ['security/ir.model.access.csv'],
}