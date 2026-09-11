# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
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
#############################################################################
{
    'name': "Advanced Dynamic Dashboard",
    'version': '16.0.2.1.3',
    'category': 'Productivity',
    'summary': """Odoo Dynamic Dashboard, Dynamic Dashboard, Odoo Dashboard, Dynamic Dashbaord, AI Dashboard, Odoo17 Dashboard, Dashboard, Odoo17, Configurable Dashboard""",
    'description': """Create Configurable Advanced Dynamic Dashboard to get the 
    information that are relevant to your 
    business, department, or a specific process or need""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['web'],
    'data': [
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
        'views/dynamic_block_views.xml',
        'views/dashboard_menu_views.xml',
        'wizard/dashboard_mail_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'advanced_dynamic_dashboard/static/lib/css/gridstack.min.css',
            'advanced_dynamic_dashboard/static/src/css/dynamic_dashboard.css',
            'advanced_dynamic_dashboard/static/src/scss/dynamic_dashboard.scss',
            'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.3/font/bootstrap-icons.css',
            'https://cdnjs.cloudflare.com/ajax/libs/gridstack.js/0.2.6/gridstack.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.3/Chart.bundle.js',
            'https://cdnjs.cloudflare.com/ajax/libs/jqueryui-touch-punch/0.2.3/jquery.ui.touch-punch.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/bootbox.js/4.4.0/bootbox.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/jspdf/1.5.3/jspdf.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.9.3/html2pdf.bundle.min.js',
            'https://cdn.jsdelivr.net/npm/exceljs@4.4.0/dist/exceljs.min.js',
            'advanced_dynamic_dashboard/static/src/js/dynamic_dashboard.js',
            'advanced_dynamic_dashboard/static/src/xml/dynamic_dashboard_template.xml',
            'https://fonts.googleapis.com/css?family=Source+Sans+Pro:300,400,400i,700',
        ],
    },
    'images': ['static/description/banner.png'],
    'license': "AGPL-3",
    'installable': True,
    'auto_install': False,
    'application': True,
    'uninstall_hook': 'uninstall_hook',
}
