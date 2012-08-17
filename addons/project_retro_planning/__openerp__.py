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
    'name': 'Project Retro-planning',
    'version': '0.1',
    'category': 'Project Management',
    'description': """
Changes dates according to change in project End Date.
======================================================

If end date of project is changed then the deadline date and start date for all
the tasks will change accordingly.
    """,
    'author': 'OpenERP SA',
    'depends': ['base', 'project'],
    'data': [],
    'data': [],
    'demo': [],
    'test' : [
              'test/deadline_change.yml'
              ],
    'installable': True,
    'auto_install': False,
    'certificate': '0057235475485',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
