# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
    'name': 'Liquid Glass Backend Theme',
    'version': '19.0.1.0.0',
    'category': 'Theme/Backend',
    'summary': 'Modern glassmorphism backend theme for Odoo',
    'description': """
        Liquid Glass Backend Theme
        A modern, elegant glassmorphism design for Odoo backend
    """,
    'author': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'LGPL-3',
    'depends': ['web', 'base'],
    'assets': {
        'web.assets_backend': [
            'theme_liquid_glass/static/src/scss/variables.scss',
            'theme_liquid_glass/static/src/scss/glass_theme.scss',
            'theme_liquid_glass/static/src/scss/buttons.scss',
            'theme_liquid_glass/static/src/scss/forms.scss',
            'theme_liquid_glass/static/src/scss/lists.scss',
            'theme_liquid_glass/static/src/scss/kanban.scss',
            'theme_liquid_glass/static/src/scss/modals.scss',
            'theme_liquid_glass/static/src/scss/navbar.scss',

        ],
        'web.assets_backend_lazy': [
            'theme_liquid_glass/static/src/js/canvas_text.js',
        ],
    },
    'images': [
        'static/description/banner.jpg',
        'static/description/theme_screenshot.jpg',
        'static/description/icon.png'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
