# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2011 OpenERP SA (<http://www.openerp.com>).
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
    "name" : "Share any Document",
    "version" : "2.0",
    "depends" : ["base", "mail"],
    "author" : "OpenERP SA",
    "category": 'Tools',
    "description": """
This module adds generic sharing tools to your current OpenERP database.
========================================================================

It specifically adds a 'share' button that is available in the Web client to
share any kind of OpenERP data with colleagues, customers, friends, etc.

The system will work by creating new users and groups on the fly, and by
combining the appropriate access rights and ir.rules to ensure that the
shared users only have access to the data that has been shared with them.

This is extremely useful for collaborative work, knowledge sharing,
synchronization with other companies, etc.

    """,
    'website': 'http://www.openerp.com',
    'demo_xml': ['share_demo.xml'],
    'data': [
        'security/share_security.xml',
        'res_users_view.xml',
        'wizard/share_wizard_view.xml'
    ],
    'installable': True,
    'web': True,
    'certificate' : '001301246528927038493',
    'js': ['static/src/js/share.js'],
    'css': ['static/src/css/share.css'],
    'qweb' : [
        "static/src/xml/*.xml",
    ],
    'images': ['images/share_wizard.jpeg','images/sharing_wizard_step1.jpeg', 'images/sharing_wizard_step2.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
