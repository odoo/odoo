{
    "name" : "Html View",
    "version" : "1.1",
    "author" : "OpenERP SA",
    "category" : "Generic Modules/Inventory Control",
    "depends" : ['base'],
    "init_xml" : ['html_view.xml'],
    "demo_xml" : [],
    "description": """
    This is the test module which shows html tag supports in normal xml form view.
    """,
    'update_xml': ['security/ir.model.access.csv','html_view.xml',],
    'installable': True,
    'active': False,
    'certificate': '',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
