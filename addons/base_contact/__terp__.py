# -*- encoding: utf-8 -*-
{
    "name" : "Base Contact",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://tinyerp.com",
    "category" : "Generic Modules/Base Contact",
    "description": """
        This module allows you to manage entirely your contacts. 

    It lets you define 
        *contacts unrelated to a partner,
        *contacts working at several adresses (possibly for different partners), 
        *contacts with possibly different functions for each of its job's addresses

    It also add new menuitems located in 
        Partners \ Contacts
        Partners \ Functions


    Pay attention that this module converts the existing addresses into "addresses + contacts". It means that some fields of the addresses will be missing (like the contact name), since these are supposed to be defined in an other object.
    """,
    "depends" : ["base", "process"],
    "init_xml" : [],
    "demo_xml" : ["base_contact_demo.xml"],
    "update_xml" : [
        "security/ir.model.access.csv",
        'base_contact_view.xml',
        "process/base_contact_process.xml"
    ],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

