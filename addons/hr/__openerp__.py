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
    'name': 'Employee Directory',
    'version': '1.1',
    'author': 'OpenERP SA',
    'category': 'Human Resources',
    'sequence': 21,
    'website': 'https://www.odoo.com',
    'summary': 'Jobs, Departments, Employees Details',
    'description': """
Human Resources Management
==========================

This application enables you to manage important aspects of your company's staff and other details such as their skills, contacts, working time...


You can manage:
---------------
* Employees and hierarchies : You can define your employee with User and display hierarchies
* HR Departments
* HR Jobs
    """,
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/employees',
    'depends': ['base_setup','mail', 'resource', 'board'],
    'data': [
        'security/hr_security.xml',
        'security/ir.model.access.csv',
        'hr_view.xml',
        'hr_installer.xml',
        'hr_data.xml',
        'res_config_view.xml',
        'mail_hr_view.xml',
        'res_users_view.xml',
        'views/hr.xml',
    ],
    'demo': ['hr_demo.xml'],
    'test': [
        'test/hr_users.yml',
        'test/open2recruit2close_job.yml',
        'test/hr_demo.yml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [ 'static/src/xml/suggestions.xml' ],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
