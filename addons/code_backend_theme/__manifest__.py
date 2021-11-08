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
    "name": "POGI Theme V15.0.1",
    "description": """Minimalist and elegant backend theme for Odoo 15, Backend Theme, Theme""",
    "summary": "Based on Code Backend Theme V15 by Cybrosys Techno Solutions",
    "category": "Theme/Backend",
    "version": "15.0.1.0.0",
    'author': 'BITS',
    'company': 'Food Group Philippines',
    'maintainer': 'BITS',
    'website': "https://www.pilmico.com",
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
            ('replace', '/web/static/src/views/graph/colors.js', '/code_backend_theme/static/src/js/fields/colors.js'),
            ('replace', '/web/static/src/views/graph/graph_renderer.js', '/code_backend_theme/static/src/js/fields/graph_renderer.js'),
            ('replace', '/web/static/src/views/graph/graph_model.js', '/code_backend_theme/static/src/js/fields/graph_model.js'),
            ('replace', '/web/static/src/views/graph/graph_arch_parser.js', '/code_backend_theme/static/src/js/fields/graph_arch_parser.js'),
            ('replace', '/web/static/src/views/graph/graph_view.js', '/code_backend_theme/static/src/js/fields/graph_view.js'),
            'code_backend_theme/static/src/js/chrome/sidebar_menu.js',
            ('replace', '/web/static/src/webclient/user_menu/user_menu.js', '/code_backend_theme/static/src/js/user_menu/user_menu.js'),
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
