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
        'views/ir_attachment_views.xml',
        'views/google_spreadsheet_templates.xml',
        'views/google_sheets_api_batch_request_format.xml',
        'data/google_drive_config_data.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}
