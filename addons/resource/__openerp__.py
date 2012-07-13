# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    "name" : "Resource",
    "version" : "1.1",
    "author" : "OpenERP SA",
    "category" : "Hidden/Dependency",
    "website" : "http://www.openerp.com",
    "description": """
Module for resource management.
===============================

A resource represent something that can be scheduled (a developer on a task or a
work center on manufacturing orders). This module manages a resource calendar
associated to every resource. It also manages the leaves of every resource.

    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['process'],
    'init_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'resource_view.xml',
    ],
    'demo_xml': ['resource_demo.xml'
    ],
    'test': [
        'test/resource.yml',
        'test/duplicate_resource.yml',
    ],
    'installable': True,
    'auto_install': False,
    'certificate': '00746371192190459469',
    'images': ['images/resource_leaves_calendar.jpeg','images/resource_leaves_form.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
