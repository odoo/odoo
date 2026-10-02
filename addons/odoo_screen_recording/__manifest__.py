# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Megha A P (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
{
    'name': "Odoo Screen Recording",
    'version': '16.0.1.0.0',
    'category': "Extra Tools",
    'summary': """Record your screen any time and store it for further use
     in odoo""",
    'description': 'Screen recording in Odoo helps to record multiple screen '
                   'at a time to store or monitor the screen activities',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'images': [
        'static/description/banner.jpg'
    ],
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/video_store_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            '/odoo_screen_recording/static/src/js/button_systray.js',
            '/odoo_screen_recording/static/src/xml/button_systray.xml',
            '/odoo_screen_recording/static/src/js/video_preview_widget.js',
            '/odoo_screen_recording/static/src/xml/video_preview_widget.xml',
        ]
    },
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
