# -*- encoding: utf-8 -*-
{
    "name" : "Customer Relationship Management",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://tinyerp.com/module_crm.html",
    "category" : "Generic Modules/CRM & SRM",
    "description": """ The Tiny ERP case and request tracker enables a group of
                   people to intelligently and efficiently manage tasks, issues,
                   and requests. It manages key tasks such as communication, 
                   identification, prioritization, assignment, resolution and notification.""",
    "depends" : ["crm","report_crm", "process", "account"],
    "init_xml" : [
                    "crm_config_view.xml",
                    "crm_bugs_view.xml",
                    "crm_jobs_view.xml",
                    "crm_lead_view.xml",
                    "crm_meeting_view.xml",
                    "crm_opportunity_view.xml",
                    "crm_fund_view.xml",
                    "crm_report_view.xml"
                 ],
    "demo_xml" : [
                    "crm_bugs_demo.xml",
                    "crm_fund_demo.xml",
                    "crm_jobs_demo.xml",
                    "crm_meeting_demo.xml",
                    "crm_lead_demo.xml",
                    "crm_opportunity_demo.xml",                    
                  ],
    "update_xml" : [
                    "crm_bugs_data.xml",  
                    "crm_fund_data.xml",                  
                    "crm_jobs_data.xml",
                    "crm_meeting_data.xml",
                    "crm_lead_data.xml",
                    "crm_opportunity_data.xml",
                    "crm_bugs_menu.xml", "crm_fund_menu.xml",
                    "crm_jobs_menu.xml", "crm_opportunity_menu.xml",
                    "crm_helpdesk_menu.xml", "crm_lead_menu.xml",
                    "crm_meeting_menu.xml",
                    "security/ir.model.access.csv",
                    "process/crm_configuration_process.xml",
                    ],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

