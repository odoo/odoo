# -*- encoding: utf-8 -*-

{
        "name" : "Idea Manager",
        "version" : "0.1",
        "author" : "Tiny",
        "website" : "http://openerp.com",
        "category" : "Tools",
        "description": """This module allows your user to easily and efficiently participate in the innovation of the enterprise. It allows everybody to express ideas about different subjects. Then, others users can comment these ideas and vote for particular ideas. Each idea as a score based on the different votes. The managers can obtain an easy view on best ideas from all the users. Once installed, check the menu 'Ideas' in the 'Tools' main menu.""", 
        "depends" : ['base'],
        "init_xml" : [ ],
        "demo_xml" : [ ],
        "update_xml" : [
            'idea_view.xml',
            'idea_workflow.xml',
            "security/idea_security.xml",
            "security/ir.model.access.csv",
            ],
        "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

