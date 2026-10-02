# Copyright 2020-21 Manish Kumar Bohra <manishkumarbohra@outlook.com> or <manishbohra1994@gmail.com>
# License LGPL-3 - See http://www.gnu.org/licenses/Lgpl-3.0.html

{
    'name': 'Product Image From URL',
    'version': '13.0',
    'summary': 'This module allows you to import product images using HTTP or HTTPS url or Local System URL',
    'description': 'This module allows you to import product images using HTTP or HTTPS url or Local System URL',
    'category': 'Sales',
    'author': 'Manish Bohra',
    'website': 'www.linkedin.com/in/manishkumarbohra',
    'maintainer': 'Manish Bohra',
    'support': 'manishkumarbohra@outlook.com',
    'sequence': '10',
    'license': 'LGPL-3',
    "data": [
        'views/product.xml',
    ],
    'images': ['static/description/banner.png'],
    'depends': ['stock'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
