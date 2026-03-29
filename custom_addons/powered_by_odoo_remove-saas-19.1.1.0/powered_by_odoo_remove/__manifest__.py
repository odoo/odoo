
# -*- coding: utf-8 -*-
#############################################################################
#
#    TugIT Software
#
#    Copyright © 2025 TugIT. All rights reserved.
#    Author: TugIT <tugitinfo@gmail.com>
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
    'name': 'Kodoo Branding Cleanup',
    # 'version': '1.0.0',
    'summary': """Remove visible Odoo promotional labels from login, portal, website and webclient.""",
    'description': """Remove visible Odoo promotional labels from login, portal, website and webclient.""",
    'author': 'TugIT Software',
    'company': 'TugIT Software',
    'maintainer': 'TugIT Software',
    'website': 'https://kodoo.online',
    'license': 'LGPL-3',
    'sequence': 10,
    'category': 'Tools',
    'depends': ['web', 'portal'],
    'data': [
        'data/kodoo_branding_data.xml',
        'views/web_layout.xml',
        'views/login_layout.xml',
        'views/portal_record_sidebar.xml',
        'views/brand_promotion.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'powered_by_odoo_remove/static/src/js/kodoo_branding.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
