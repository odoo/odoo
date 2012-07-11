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
    "name": "Employee Directory",
    "version": "1.1",
    "author": "OpenERP SA",
    "category": "Human Resources",
    "sequence": 12,
    "website": "http://www.openerp.com",
    "description": """
Module for Human Resource Management.
=====================================

You can manage:
    * Employees and hierarchies : You can define your employee with User and display hierarchies
    * HR Departments
    * HR Jobs
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/hr_department.jpeg', 'images/hr_employee.jpeg','images/hr_job_position.jpeg'],
    'depends': ['base_setup','mail', 'resource', 'board'],
    'init_xml': [],
    'update_xml': [
        'security/hr_security.xml',
        'security/ir.model.access.csv',
        'board_hr_view.xml',
        'hr_view.xml',
        'hr_department_view.xml',
        'process/hr_process.xml',
        'hr_installer.xml',
        'hr_data.xml',
        'res_config_view.xml',
    ],
    'demo_xml': [
        'hr_demo.xml',
    ],
    'test': [
             'test/open2recruit2close_job.yml',
             'test/hr_demo.yml',
             ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'certificate': '0086710558965',
    "css": [ 'static/src/css/hr.css' ],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
