# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Google Spreadsheet',
    'version': '1.0',
    'category': 'Tools',
    'description': """
The module adds the possibility to display data from OpenERP in Google Spreadsheets in real time.
=================================================================================================
""",
    'depends': ['google_drive'],
    'data' : [
        'google_spreadsheet_view.xml',
        'google_spreadsheet_data.xml',
        'views/google_spreadsheet.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
