# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    "name" : "",
    "version" : "1.1",
    "depends" : ['marketing_campaign'],
    "author" : "OpenERP SA",
    "category": 'Generic Modules/Marketing',
    "description": """    
    This module provides integration of the mailchimp.com marketing campaign and mailing-list service, connecting via Mailchimp's WebServices API.
    You can define multiple Mailchimp accounts and then use them as you wish through a new type of activity, providing direct connection to your Mailchimp Lists.""",
    'website': 'http://www.openerp.com',
    'init_xml': [],
    'update_xml': [
        "security/ir.model.access.csv",
        'marketing_campaign_mailchimp_view.xml',
        'wizard/create_list_view.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
