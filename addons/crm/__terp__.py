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
    'name': 'Customer & Supplier Relationship Management',
    'version': '1.0',
    'category': 'Generic Modules/CRM & SRM',
    'description': """The generic Open ERP Customer Relationship Management
system enables a group of people to intelligently and efficiently manage
leads, opportunities, claims, meeting, phonecall etc.
It manages key tasks such as communication, identification, prioritization,
assignment, resolution and notification.

Open ERP ensures that all cases are successfully tracked by users, customers and
suppliers. It can automatically send reminders, escalate the request, trigger
specific methods and lots of others actions based on your enterprise own rules.

The greatest thing about this system is that users don't need to do anything
special. They can just send email to the request tracker. Open ERP will take
care of thanking them for their message, automatically routing it to the
appropriate staff, and making sure all future correspondence gets to the right
place.

The CRM module has a email gateway for the synchronisation interface
between mails and Open ERP.""", 
    'author': 'Tiny', 
    'website': 'http://www.openerp.com', 
    'depends': ['base', 'base_action_rule',                         
                        'process', 
                        'mail_gateway', 
                        'base_calendar',
                    ], 
    'init_xml': ['crm_data.xml', 
                'crm_meeting_data.xml', 
                 'crm_claims_data.xml', 
                 'crm_fund_data.xml', 
                 'crm_helpdesk_data.xml', 
                 'crm_lead_data.xml', 
                 'crm_meeting_data.xml', 
                 'crm_opportunity_data.xml', 
                 'crm_phonecall_data.xml', 
    ], 

    'update_xml': [
        'wizard/crm_lead_to_partner_view.xml',
        'wizard/crm_lead_to_opportunity_view.xml',

        'wizard/crm_phonecall_to_phonecall_view.xml',
        'wizard/crm_phonecall_to_meeting_view.xml',
        'wizard/crm_phonecall_to_partner_view.xml',
        'wizard/crm_phonecall_to_opportunity_view.xml',

        'wizard/crm_opportunity_to_meeting_view.xml',
        'wizard/crm_opportunity_to_phonecall_view.xml',
        'wizard/crm_partner_to_opportunity_view.xml',
        
        'wizard/crm_send_email_view.xml', 
        'wizard/crm_email_add_cc_view.xml',  
        'crm_wizard.xml', 
        'crm_view.xml',
         
        'crm_action_rule_view.xml', 
        'crm_lead_view.xml', 
        'crm_lead_menu.xml', 
        'crm_meeting_view.xml', 
        'crm_meeting_menu.xml', 
        'crm_phonecall_view.xml', 
        'crm_phonecall_menu.xml',         
        'crm_opportunity_view.xml', 
        'crm_opportunity_menu.xml', 
        'crm_fund_view.xml', 
        'crm_fund_menu.xml', 
        'crm_claims_view.xml', 
        'crm_claims_menu.xml', 

        'crm_helpdesk_view.xml',
        'crm_helpdesk_menu.xml', 
         
        'security/crm_security.xml', 
        'security/ir.model.access.csv', 

        'report/crm_report_view.xml',
        'report/crm_claim_report_view.xml',
        'report/crm_lead_report_view.xml',
        'report/crm_fundraising_report_view.xml',
        'report/crm_opportunity_report_view.xml' ,       
        'report/crm_phonecall_report_view.xml',
        
        'process/crm_configuration_process.xml',
        
    ],
    'demo_xml': [
        'crm_demo.xml', 
        'crm_claims_demo.xml', 
        'crm_fund_demo.xml', 
        'crm_helpdesk_demo.xml', 
        'crm_lead_demo.xml', 
        'crm_meeting_demo.xml', 
        'crm_opportunity_demo.xml', 
        'crm_phonecall_demo.xml'], 
    'installable': True, 
    'active': False, 
    'certificate': '0079056041421', 
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
