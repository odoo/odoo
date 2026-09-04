# Copyright 2020 Manish Kumar Bohra <manishbohra1994@gmail.com> or <manishkumarbohra@outlook.com>
# License LGPL-3 - See http://www.gnu.org/licenses/Lgpl-3.0.html

{
    'name': 'Hide Powered by and Manage DB Link',
    'version': '1.0',
    'summary': 'This module allows hide powered by and manage DB link from the login page',
    'description': 'This module allows hide powered by and manage DB link from the login page',
    'category': 'Other',
    'author': 'Manish Bohra',
    'website': 'www.linkedin.com/in/manishkumarbohra',
    'maintainer': 'Manish Bohra',
    'support': 'manishkumarbohra@outlook.com',
    'sequence': '10',
    'license': 'LGPL-3',
    "data": [
        'views/webclient_templates.xml',
    ],
    'images': ['static/description/banner.png'],
    'depends': ['web'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
