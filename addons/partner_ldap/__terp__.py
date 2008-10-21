# -*- encoding: utf-8 -*-
{
    "name" : "Partner extension to synchronize TinyERP with ldap",
    "version" : "1.0",
    "author" : "Tiny",
    "depends" : ["base", "hr", "process"],
    "category" : "Generic Modules/Inventory Control",
    "description": "Synchronise partners through a LDAP module. Has been used to synchronise partners in Outlook and Tiny ERP.",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : ["wizard.xml", 
                    "process/partner_ldap_process.xml"
                    ],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

