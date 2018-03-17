# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2017-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Hilar AK(<hilar@cybrosys.in>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': "Odoo Debranding",
    'version': "10.0.1.0",
    'summary': """Debrand Odoo""",
    'description': """Debrand Odoo""",
    'author': "Cybrosys Techno Solutions",
    'company': "Cybrosys Techno Solutions",
    'website': "https://cybrosys.com/",
    'category': 'Tools',
    'depends': ['base', 'im_livechat', 'website'],
    'data': [
        'views/views.xml',
        'views/templates.xml'],
    'demo': [],
    'qweb': ["static/src/xml/*.xml"],
    'images': ['static/description/banner.jpg'],
    'license': "LGPL-3",
    'installable': True,
    'application': False
}
