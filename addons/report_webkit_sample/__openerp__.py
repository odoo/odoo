# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com)
# All Right Reserved
#
# Author : Nicolas Bessi (Camptocamp)
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

{
    'name': 'Webkit Report Samples',
    'description': """
Samples for Webkit Report Engine (report_webkit module).
========================================================

A sample invoice report is included in this module, as well as a wizard to
add Webkit Report entries on any Document in the system.

You have to create the print buttons by calling the wizard. For more details see:
    http://files.me.com/nbessi/06n92k.mov
""",
    'version': '0.9',
    'depends': ['base', 'account', 'report_webkit'],
    'category': 'Reporting',
    'author': 'Camptocamp SA - NBessi',
    'url': 'http://www.camptocamp.com/',
    'data': ['report_webkit_html_view.xml'],
    'installable': True,
    'auto_install': False,
    'certificate': '00436592682591421981',
    'images': ['images/webkit_invoice_report.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
