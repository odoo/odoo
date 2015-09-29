# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com)
# Author : Nicolas Bessi (Camptocamp)

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
This module requires the ``wkhtmltopdf`` library to render HTML documents as
PDF. Version 0.9.9 or later is necessary, and can be found at
http://code.google.com/p/wkhtmltopdf/ for Linux, Mac OS X (i386) and Windows (32bits).

After installing the library on the OpenERP Server machine, you may need to set
the path to the ``wkhtmltopdf`` executable file in a system parameter named
``webkit_path`` in Settings -> Customization -> Parameters -> System Parameters

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
    'depends': ['base','report'],
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
    'demo': [
        "report/webkit_report_demo.xml",
    ],
    'test': [
        "test/print.yml",
    ],
    'installable': True,
    'auto_install': False,
}
