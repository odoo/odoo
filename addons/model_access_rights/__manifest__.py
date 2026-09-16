# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
    'name': 'Hide Create|Delete|Archive|Export Options - Model Wise',
    'version': '16.0.1.0.0',
    'category': 'Extra Tools, Productivity',
    'summary': """ Can hide options from user """,
    'description': """ By using this module we can hide the options like create,
    delete,export,and archive/un archive in the model which we want. Here we
     are also able to select the user groups except Administrator which we want 
     to apply the above hiding functionality """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['base_setup', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/model_access_rights_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'model_access_rights/static/src/js/form_controller.js',
            'model_access_rights/static/src/js/list_controller.js',
            'model_access_rights/static/src/js/kanban_controller.js'
        ]
    },
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
