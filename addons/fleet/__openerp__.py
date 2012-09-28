# -*- coding: utf-8 -*-
{
    'name' : 'Fleet Management',
    'version' : '0.1',
    'author' : 'OpenERP S.A.',
    'category': 'Fleet Management',
    'website' : 'http://www.openerp.com',
    'summary' : 'Manage your fleet of vehicle',
    'description' : """
Easy way to manage your fleet
===============================

With this easy to use module, you can in a few clicks manage your entire vehicle fleet.

Managing a single vehicle or thousands of them has never been easier.

Encode your vehicle, group them with tags, view the ones that interest you with the search function.

Add insurance and services reminder that will help you by sending you a mail when you need to renew the insurance of a vehicle or do the next maintenance.
""",
    'depends' : [
        'base',
        'mail',
    ],
    'data' : [
        'fleet_view.xml',
    ],
    'update_xml' : ['security/ir.model.access.csv'],
    'demo': ['demo.xml'],
    'installable' : True,
    'application' : True,
}