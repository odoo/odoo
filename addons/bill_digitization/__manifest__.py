# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Sruthi Renjith (odoo@cybrosys.com)
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
################################################################################
{
    'name': 'Bill Digitization',
    'version': '16.0.1.0.0',
    'category': 'Accounting',
    'summary': """Converting traditional paper-based bills into digital 
     formats.""",
    'description': """Reading scanned documents with extension .jpg, .jpeg and 
    .png using specialized hardware and converting them into
     vendor bills in odoo. It makes use of the Optical Character 
     Recognition (OCR) technology to convert scanned images into
     editable text""",
    'author': "Cybrosys Techno Solutions",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['base', 'base_accounting_kit'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'wizard/digitize_bill_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bill_digitization/static/src/js/digitize_button.js',
            'bill_digitization/static/src/xml/digitize_button.xml',
        ],
    },
    'external_dependencies': {
        'python': ['PIL', 'pytesseract']
    },
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}
