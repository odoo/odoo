# -*- coding: utf-8 -*-
{
    'name': 'Collaborative Pads',
    'version': '2.0',
    'category': 'Project Management',
    'description': """
Adds enhanced support for (Ether)Pad attachments in the web client.
===================================================================

Lets the company customize which Pad installation should be used to link to new
pads (by default, http://ietherpad.com/).
    """,
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'depends': ['base'],
    'data': ['res_company.xml'],
    'demo': ['pad_demo.xml'],
    'installable': True,
    'auto_install': False,
    'web': True,
    'js': ['static/src/js/pad.js'],
    'qweb' : ['static/src/xml/*.xml'],
    'images': ['static/src/img/pad_link_companies.jpeg'],
    'css': ['static/src/css/etherpad.css',],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
