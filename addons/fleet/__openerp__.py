# -*- coding: utf-8 -*-
{
    'name' : 'Fleet Management',
    'version' : '0.1',
    'author' : 'OpenERP S.A.',
    'category': 'Vehicle, leasing, insurances, costs',
    'website' : 'http://www.openerp.com',
    'summary' : 'Manage all your vehicles and contracts',
    'description' : """
Vehicle, leasing, insurances, cost
==================================


""",
    'depends' : [
        'base',
        'mail',
        'board'
    ],
    'data' : [
        'fleet_view.xml',
        'data.xml',
        'board_fleet_view.xml'
    ],
    'update_xml' : ['security/ir.model.access.csv'],

    'demo': ['cars.xml','demo.xml'],

    'installable' : True,
    'application' : True,
}