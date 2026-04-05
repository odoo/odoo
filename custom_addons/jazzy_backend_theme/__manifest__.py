# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
    "name": "Jazzy Backend Theme",
    "version": "19.0.1.0.0",
    "category": "Themes/Backend",
    "summary": "Jazzy backed Theme is an attractive theme for backend",
    "description": """Minimalist and elegant backend theme for Odoo Backend""",
    "author": "Cybrosys Techno Solutions",
    "company": "Cybrosys Techno Solutions",
    "maintainer": "Cybrosys Techno Solutions",
    "website": "https://www.cybrosys.com",
    "depends": ["web", "mail"],
    "data": [
        'views/layout_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'jazzy_backend_theme/static/src/components/app_menu/side_menu.xml',
            'jazzy_backend_theme/static/src/layout/style/layout_colors.scss',
            'jazzy_backend_theme/static/src/components/app_menu/menu_order.css',
            'jazzy_backend_theme/static/src/layout/style/layout_style.scss',
            'jazzy_backend_theme/static/src/layout/style/sidebar.scss',
            'jazzy_backend_theme/static/src/components/app_menu/search_apps.js',
        ],
        'web.assets_frontend': [
            'jazzy_backend_theme/static/src/layout/style/login.scss'
        ],
    },
    'images': [
        'static/description/banner.jpg',
        'static/description/theme_screenshot.jpg',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
