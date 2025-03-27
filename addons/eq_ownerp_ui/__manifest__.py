# -*- coding: utf-8 -*-
# Copyright 2014-now Equitania Software GmbH - Pforzheim - Germany
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'EQ Backend UI',
    'license': 'AGPL-3',
    'version': '1.0.7',
    'description': "Easy configurable Backend Theme",
    'author': 'Equitania Software GmbH',
    'website': 'https://www.ownerp.com',
    'depends': ['base_setup','web'],
    'category': 'Extra Tools',
    'summary': 'Choose your colors for Backend',
    'images': ['static/description/banner.gif'],
    'data': [
        "data/eq_default_view.xml",
        "data/eq_default_templates.xml",
        "security/ir.model.access.csv",
        "views/eq_template_colors.xml",
        "views/eq_colors.xml"
    ],
    'assets': {
        'web.assets_backend': [
            '/eq_ownerp_ui/static/src/lib/bootstrap-colorpicker/css/bootstrap-colorpicker.min.css',
            '/eq_ownerp_ui/static/src/lib/bootstrap-colorpicker/js/bootstrap-colorpicker.js',
            '/eq_ownerp_ui/static/src/js/eq_widgets.js',
            '/eq_ownerp_ui/static/src/xml/eq_color_widget.xml',
            '/eq_ownerp_ui/static/src/css/eq_color_widget.css'
        ],
    },
    'qweb': [],
    'demo': [],
    'css': ['base.css'],
    'installable': True,
    'auto_install': False,
}
