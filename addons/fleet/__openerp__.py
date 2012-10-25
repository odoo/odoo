# -*- coding: utf-8 -*-
{
    'name' : 'Fleet Management',
    'version' : '0.1',
    'author' : 'OpenERP S.A.',
    'category': 'Managing vehicles and contracts',
    'website' : 'http://www.openerp.com',
    'summary' : 'Vehicle, leasing, insurances, costs',
    'description' : """
Vehicle, leasing, insurances, cost
==================================
With this module, OpenERP helps you managing all your vehicles, the
contracts associated to those vehicle as well as services, fuel log
entries, costs and many other features necessary to the management 
of your fleet of vehicle(s)

Main Features
-------------
* Add vehicles to your fleet
* Manage contracts for vehicles
* Reminder when a contract reach its expiration date
* Add services, fuel log entry, odometer values for all vehicles
* Show all costs associated to a vehicle or to a type of service
* Analysis graph for costs
""",
    'depends' : [
        'base',
        'mail',
        'board'
    ],
    'data' : [
        'fleet_view.xml',
        'data.xml',
        'board_fleet_view.xml',
    ],
    'update_xml' : ['security/ir.model.access.csv'],

    'demo': ['cars.xml','demo.xml'],

    'installable' : True,
    'application' : True,
}