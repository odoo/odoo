# -*- encoding: utf-8 -*-
#
# you must set the depends variable on modules you plan to audit !
#
{
    "name" : "Audit Trail",
    "version" : "1.0",
    "depends" : ["base","account","purchase","mrp"],
    "website" : "http://tinyerp.com",
    "author" : "Tiny",
    "init_xml" : [],
    "description": "Allows the administrator to track every user operations on all objects of the system.",
    "category" : "Generic Modules/Others",
    "update_xml" : ["audittrail_view.xml", 
                    "security/ir.model.access.csv",
                    "security/audittrail_security.xml",
                   ],
    "demo_xml" : ["audittrail_demo.xml"],
    "active" : False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

