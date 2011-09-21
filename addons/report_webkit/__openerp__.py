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
    "name" : "Webkit Report Engine",
    "description" : """
This module adds a new Report Engine based on WebKit library (wkhtmltopdf) to support reports designed in HTML + CSS.
=====================================================================================================================

The module structure and some code is inspired by the report_openoffice module.

The module allows:
    -HTML report definition
    -Multi header support
    -Multi logo
    -Multi company support
    -HTML and CSS-3 support (In the limit of the actual WebKIT version)
    -JavaScript support
    -Raw HTML debugger
    -Book printing capabilities
    -Margins definition
    -Paper size definition

... and much more

Multiple headers and logos can be defined per company.
CSS style, header and footer body are defined per company

The library to install can be found here
http://code.google.com/p/wkhtmltopdf/
The system libraries are available for Linux, Mac OS X i386 and Windows 32.

After installing the wkhtmltopdf library on the OpenERP Server machine, you need to set the
path to the wkthtmltopdf executable file on the Company.

For a sample report see also the webkit_report_sample module, and this video:
    http://files.me.com/nbessi/06n92k.mov


TODO :
JavaScript support activation deactivation
Collated and book format support
Zip return for separated PDF
Web client WYSIWYG
                    """,
    "version" : "0.9",
    "depends" : ["base"],
    "author" : "Camptocamp",
    "category": "Tools",
    "url": "http://http://www.camptocamp.com/",
    "data": [ "security/ir.model.access.csv",
              "data.xml",
              "wizard/report_webkit_actions_view.xml",
              "company_view.xml",
              "header_view.xml",
              "ir_report_view.xml",
    ],
    "installable" : True,
    "active" : False,
    "certificate" : "001159699313338995949",
    'images': ['images/companies_webkit.jpeg','images/header_html.jpeg','images/header_img.jpeg'],
}
