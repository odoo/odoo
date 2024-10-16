# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
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
###############################################################################
{
    'name': 'Twilio SMS Gateway',
    'version': '17.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Facilitating individual and group SMS communication through '
               'the Twilio gateway.',
    'description': 'This module empowers seamless SMS communication via '
                   'Twilio, enabling users to send messages directly from '
                   #'sale orders and purchase orders. 
                   'Users can conveniently '
                   'create and utilize message templates for efficient '
                   'communication. Additionally, the module facilitates group '
                   'messaging, allowing users to send SMS to multiple '
                   'recipients simultaneously.',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['crm'],
    'data': [
            'data/ir_cron_data.xml',
            'security/ir.model.access.csv',
            #'views/purchase_order_views.xml',
            'views/res_partner_views.xml',
            #'views/sale_order_views.xml',
            'views/twilio_account_views.xml',
            'views/twilio_sms_group_views.xml',
            'views/twilio_sms_template_views.xml',
            'views/twilio_sms_views.xml',
            'views/crm_lead_views.xml',
            'wizard/sms_builder_views.xml'
    ],
    'external_dependencies': {
        'python': ['twilio']
        },
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
