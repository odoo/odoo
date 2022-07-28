# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2021-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

{
    "name": "Code Backend Theme V15",
    "description": """Minimalist and elegant backend theme for Odoo 14, Backend Theme, Theme""",
    "summary": "Code Backend Theme V15 is an attractive theme for backend",
    "category": "Themes/Backend",
    "version": "15.0.1.0.4",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    "depends": ['base', 'web', 'mail'],
    "data": [
        'views/icons.xml',
        'views/layout.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'code_backend_theme/static/src/scss/login.scss',
        ],
        'web.assets_backend': [
            'code_backend_theme/static/src/scss/theme_accent.scss',
            'code_backend_theme/static/src/scss/navigation_bar.scss',
            'code_backend_theme/static/src/scss/datetimepicker.scss',
            'code_backend_theme/static/src/scss/theme.scss',
            'code_backend_theme/static/src/scss/sidebar.scss',

            'code_backend_theme/static/src/js/fields/colors.js',
            'code_backend_theme/static/src/js/chrome/sidebar_menu.js',
        ],
        'web.assets_qweb': [
            'code_backend_theme/static/src/xml/styles.xml',
            'code_backend_theme/static/src/xml/top_bar.xml',
        ],
    },
    'images': [
        'static/description/banner.png',
        'static/description/theme_screenshot.png',
    ],
    'license': 'LGPL-3',
    'pre_init_hook': 'test_pre_init_hook',
    'post_init_hook': 'test_post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
