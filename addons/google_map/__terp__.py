# -*- encoding: utf-8 -*-
{
    "name" : "Google Map",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://tinyerp.com",
    "category" : "Generic Modules",
    "description": """The module adds google map field in partner address
so that we can directly open google map from the
url widget.""",
    "depends" : ["base"],
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : ["google_map_wizard.xml","google_map_view.xml"],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

