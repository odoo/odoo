###################################################################################
#
#    Odoo, Odoo Debranding
#    Copyright (C) 2020 Hilar AK All Rights Reserved
#    https://www.linkedin.com/in/hilar-ak/
#    <hilarak@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################
{
    'name': "Odoo Debranding",

    'summary': """
        Odoo Module for backend and frontend debranding.""",

    'description': """
        To debrand front-end and back-end pages by removing
         odoo promotions, links, labels and other related
         stuffs.
    """,

    'author': "Hilar AK",
    'website': "https://www.linkedin.com/in/hilar-ak/",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'tools',
    'version': '14.2.1.0.0',
    'license': 'LGPL-3',
    'price': 49.99,
    'currency': 'USD',
    'depends': [
        'base_setup',
        'website',
        'mail',
    ],
    'data': [
        'data/mailbot_data.xml',
        'views/views.xml',
    ],
    'qweb': ['static/src/xml/base.xml'],
    'images': ["static/description/banner.gif"],
    'installable': True,
    'application': True,
    "pre_init_hook": "pre_init_check",
}
