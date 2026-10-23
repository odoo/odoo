# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Customize Title Header',
    'version': '16.0.1.0.0',
    'sequence': 1,
    'summary': """
        Custom shortcut title, Odoo Favicon Title, Odoo Title and Favicon, Odoo Backend Title Favicon, Odoo Web Favicon Title, 
        Odoo Web Title, Odoo Customize Title Header, Odoo Browser Header, Odoo Header Favicon, Odoo Header Title, Web Window Title, 
        Web Backend Title, Odoo Backend Title, Web Responsive Title, Remove Odoo Favicon Header, Remove Odoo Title, Hide Odoo Title,
        Remove Favicon Header, Web Odoo Shortcut Favicon Shortcut Odoo Shortcut, Odoo Backend Favicon Odoo Backend Title Odoo Browser,
        Customization Favicon Title Customization, Configutable Favicon Title Configutable, Configution Favicon Title Configution, 
        Web Shortcut Customization Shortcut Editable Favicon Editable Shortcut Favicon Setup Title Header Title Browser Title Navigator
    """,
    'description': "Choose your own Title to display on the browser header.",
    'author': 'Innoway',
    'maintainer': 'Innoway',
    'price': '0.0',
    'currency': 'USD',
    'website': 'https://innoway-solutions.com',
    'license': 'LGPL-3',
    'images': [
        'static/description/wallpaper.png'
    ],
    'depends': [
        'web'
    ],
    'data': [
        
    ],
    'assets': {
        'web.assets_backend_prod_only': [
            'customize_title_header/static/src/js/favicon.js',
        ],
    },
    'demo': [

    ],
    'installable': True,
    'application': True,
    'auto_install': True,
    'qweb': [
        
    ],
}
