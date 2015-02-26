# -*- coding: utf-8 -*-

{
    'name': 'Google Spreadsheet',
    'version': '1.0',
    'category': 'Tools',
    'description': """
The module adds the possibility to display data from Odoo in Google Spreadsheets in real time.
=================================================================================================
""",
    'author': 'Odoo S.A.',
    'website': 'https://www.odoo.com',
    'depends': ['board', 'google_drive'],
    'data': [
        'views/google_spreadsheet_view.xml',
        'views/google_spreadsheet.xml',
        'data/google_spreadsheet_data.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}
