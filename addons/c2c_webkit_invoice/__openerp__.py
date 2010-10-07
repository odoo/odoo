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
    "name" : "webkit report",
    "description" : """Sample webkit Invoice Report  base on WebKit engine (wkhtmltopd lib) that allows to do HTML2PDF reporting.

    A sample invoice report is defined . 
    You have to create the print button by calling a wizard. For more details :
        http://files.me.com/nbessi/06n92k.mov 
                    """,
    "version" : "0.9",
    "depends" : ["base", "account","c2c_webkit_report"],
    "author" : "Camptocamp SA - NBessi",
    "init_xml" : ['data.xml'],
    "update_xml": [     
                        "wizard_report_actions_view.xml",
                        "report_webkit_html_view.xml",
                   ],
    "installable" : True,
    "active" : False,
}