# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Technologies (<https://www.cybrosys.com>)
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
    'name': "CRM Dashboard",
    'version': '19.0.1.0.0',
    'category': 'Extra Tools',
    'summary': """Get a visual report of CRM through a Dashboard in CRM """,
    'description': """CRM dashboard module brings a multipurpose graphical
     dashboard for CRM module and making the relationship management 
     better and easier""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['crm', 'sale_management'],
    'data': ['views/crm_dashboard_views.xml',
             'views/res_users_views.xml',
             'views/utm_campaign_views.xml',
             'views/crm_team_views.xml',
             ],
    'assets': {
        'web.assets_backend': [
            'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js',
            'crm_dashboard/static/src/css/style.css',
            'crm_dashboard/static/src/js/crm_dashboard.js',
            'crm_dashboard/static/src/xml/dashboard_templates.xml',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'application': True,
    'auto_install': True,
}
