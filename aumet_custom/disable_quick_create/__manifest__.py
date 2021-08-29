# -*- coding: utf-8 -*-
# © 2017-2018 Savoir-faire Linux
# License LGPL-3.0 or later (http://www.gnu.org/licenses/LGPL).

{
    'name': 'Disable Quick Create',
    'category': 'Web',
    'summary': 'Disable "quick create" for all and "create and edit" '
               'for specific models',
    'depends': [
        'web',
    ],
    'data': [
        'views/disable_quick_create.xml',
        'views/ir_model.xml',
    ],
    'installable': True,
    'application': False,
}
