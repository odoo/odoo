
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
    'name': 'Remove Powered by Odoo',
    # 'version': '1.0.0',
    'summary': """Remove Powered by Odoo from Login, Portal and Brand Promotion from website footer. 
    Remove Odoo branding from the footer of portal pages. Connect with your software 
    Removing the 'Powered by' block entirely 
        Remove from the portal sidebar.
        Remove from the login page.
        Remove from the brand promotion.
        Remove Odoo branding from the footer of portal pages.
        Remove branding
        De branding Odoo
        Hide Powered by odoo
        login page
        connect with your software
        odoo signin page
        odoo signup page
        odoo sign screen
        hide connect with your software
    """,
    'description': """ Remove Powered by Odoo from Portal
        Removing the 'Powered by' block entirely 
        Remove from the portal sidebar.
        Remove from the login page.
        Remove from the brand promotion.
        Remove Odoo branding from the footer of portal pages.
        Remove branding
        Hide Powered by odoo
        login page
    """,
    'author': 'TugIT Software',
    'company': 'TugIT Software',
    'maintainer': 'TugIT Software',
    'website': 'https://tugit.odoo.com',
    'license': 'LGPL-3',
    'sequence': 10,
    'category': 'Tools',
    'depends': ['portal'],
    'data': [
        'views/login_layout.xml',
        'views/portal_record_sidebar.xml',
        'views/brand_promotion.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
