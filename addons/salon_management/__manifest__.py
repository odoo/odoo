# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2020-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
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
    'summary': """Beauty Parlour Management with Online Booking System""",
    'version': '14.0.1.0.0',
    'author': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'company': 'Cybrosys Techno Solutions',
    "category": "Industries",
    'depends': ['base','base_setup', 'account', 'mail', 'website'],
    'data': [
             'security/salon_security.xml',
             'security/ir.model.access.csv',
             'data/data_chair.xml',
             'data/data_booking.xml',
             'views/salon_holiday.xml',
             'views/js_view.xml',
             'views/salon_data.xml',
             'views/salon_management_chair.xml',
             'views/salon_management_services.xml',
             'views/salon_order_view.xml',
             'views/salon_management_dashboard.xml',
             'views/booking_backend.xml',
             'views/salon_email_template.xml',
             'views/salon_config.xml',
             'views/working_hours.xml',
             'templates/salon_booking_templates.xml',
             ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'application': True,
}
