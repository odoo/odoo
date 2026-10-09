# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2021-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################
{
    'name': 'Beauty Spa Management',
    'summary': 'Beauty Parlour Management with Online Booking System',
    'version': '16.0.2.0.1',
    'author': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'live_test_url':
        'https://www.youtube.com/watch?v=TFmupz8MRm0&feature=youtu.be',
    "category": "Services",
    'depends': ['account', 'base', 'base_setup', 'mail', 'website', 'contacts'],
    'data': [
        'security/salon_management_groups.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/mail_template.xml',
        'data/salon_chair_data.xml',
        'data/salon_holiday_data.xml',
        'data/salon_order_data.xml',
        'data/salon_stages_data.xml',
        'data/salon_working_hours_data.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/salon_booking_templates.xml',
        'views/salon_booking_views.xml',
        'views/salon_order_views.xml',
        'views/salon_chairs.xml',
        'views/salon_management_views.xml',
        'views/salon_management_menus.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'salon_management/static/src/css/salon_dashboard.css',
            'salon_management/static/src/xml/salon_dashboard.xml',
            'salon_management/static/src/js/salon_dashboard.js',
            # 'salon_management/static/src/js/salon_chair.js',
        ],
        'web.assets_frontend': [
            'salon_management/static/src/css/salon_website.css',
            'salon_management/static/src/js/website_salon_booking.js',
        ],
    },
}
