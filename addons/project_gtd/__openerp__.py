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
    'name': 'Todo Lists',
    'version': '1.0',
    'category': 'Project Management',
    'sequence': 100,
    'summary': 'Personal Tasks, Contexts, Timeboxes',
    'description': """
Implement concepts of the "Getting Things Done" methodology 
===========================================================

This module implements a simple personal to-do list based on tasks. It adds an editable list of tasks simplified to the minimum required fields in the project application.

The to-do list is based on the GTD methodology. This world-wide used methodology is used for personal time management improvement.

Getting Things Done (commonly abbreviated as GTD) is an action management method created by David Allen, and described in a book of the same name.

GTD rests on the principle that a person needs to move tasks out of the mind by recording them externally. That way, the mind is freed from the job of remembering everything that needs to be done, and can concentrate on actually performing those tasks.
    """,
    'author': 'OpenERP SA',
    'images': ['images/project_gtd.jpeg'],
    'depends': ['project'],
    'data': [
        'project_gtd_data.xml',
        'project_gtd_view.xml',
        'security/ir.model.access.csv',
        'wizard/project_gtd_empty_view.xml',
        'wizard/project_gtd_fill_view.xml',
    ],
    'demo': ['project_gtd_demo.xml'],
    'test':['test/task_timebox.yml'],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
