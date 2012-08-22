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
    'name': 'Webkit Report Engine',
    'description': """
This module adds a new Report Engine based on WebKit library (wkhtmltopdf) to support reports designed in HTML + CSS.
=====================================================================================================================

The module structure and some code is inspired by the report_openoffice module.

The module allows:
------------------
    - HTML report definition
    - Multi header support
    - Multi logo
    - Multi company support
    - HTML and CSS-3 support (In the limit of the actual WebKIT version)
    - JavaScript support
    - Raw HTML debugger
    - Book printing capabilities
    - Margins definition
    - Paper size definition

Multiple headers and logos can be defined per company. CSS style, header and
footer body are defined per company.

For a sample report see also the webkit_report_sample module, and this video:
    http://files.me.com/nbessi/06n92k.mov

Requirements and Installation:
------------------------------
This module requires the ``wkthtmltopdf`` library to render HTML documents as
PDF. Version 0.9.9 or later is necessary, and can be found at
http://code.google.com/p/wkhtmltopdf/ for Linux, Mac OS X (i386) and Windows (32bits).

After installing the library on the OpenERP Server machine, you need to set the
path to the ``wkthtmltopdf`` executable file on each Company.

If you are experiencing missing header/footer problems on Linux, be sure to
install a 'static' version of the library. The default ``wkhtmltopdf`` on
Ubuntu is known to have this issue.


TODO:
-----
    * JavaScript support activation deactivation
    * Collated and book format support
    * Zip return for separated PDF
    * Web client WYSIWYG
""",
    'version': '0.9',
    'depends': ['base'],
    'author': 'Camptocamp',
    'category': 'Reporting', # i.e a technical module, not shown in Application install menu
    'url': 'http://http://www.camptocamp.com/',
    'data': [ 'security/ir.model.access.csv',
              'data.xml',
              'wizard/report_webkit_actions_view.xml',
              'company_view.xml',
              'header_view.xml',
              'ir_report_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'certificate': '001159699313338995949',
    'images': ['images/companies_webkit.jpeg','images/header_html.jpeg','images/header_img.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
