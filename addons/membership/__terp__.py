# -*- encoding: utf-8 -*-
{
    "name" : "Membership",
    "version" : "0.1",
    "author" : "Tiny",
    "category" : "Generic Modules/Association",
    "depends" : [
        "base", "product", "account", "process"
        ],
    "demo_xml" : [
        #"demo_data.xml",
        "membership_demo.xml"
        ],
    "init_xml" : [
        "membership_data.xml",
        ],
    "update_xml" : [
        "security/ir.model.access.csv",
        "membership_view.xml","membership_wizard.xml",
        "process/membership_process.xml"
        ],
    "active" : False,
    "installable" : True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

