{
    "name" : "Html View",
    "version" : "1.1",
    "author" : "OpenERP SA",
    "category" : "Tools",
    "depends" : ['base'],
    "init_xml" : ['html_view.xml'],
    "demo_xml" : [],
    "description": """
    This is the test module which shows html tag supports in normal xml form view.
    """,
    'update_xml': ['security/ir.model.access.csv','html_view.xml',],
    'installable': True,
    'active': False,
    'certificate': '001302129363003126557',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
