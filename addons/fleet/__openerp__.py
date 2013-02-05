# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name' : 'Fleet Management',
    'version' : '0.1',
    'author' : 'OpenERP S.A.',
    'sequence': 110,
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
        'fleet_cars.xml',
        'fleet_data.xml',
        'fleet_board_view.xml',
    ],
    'images': ['images/costs_analysis.jpeg','images/indicative_costs_analysis.jpeg','images/vehicles.jpeg','images/vehicles_contracts.jpeg','images/vehicles_fuel.jpeg','images/vehicles_odometer.jpeg','images/vehicles_services.jpeg'],
    'update_xml' : ['security/fleet_security.xml','security/ir.model.access.csv'],

    'demo': ['fleet_demo.xml'],

    'installable' : True,
    'application' : True,
}
