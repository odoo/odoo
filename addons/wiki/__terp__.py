

{
    'name': 'Document Management - Wiki',
    'version': '1.0',
    'category': 'Generic Modules/Others',
    'description': """
    The base module to manage documents(wiki) 
    
    keep track for the wiki groups, pages, and history
    """,
    'author': 'Tiny & Axelor',
    'website': 'http://openerp.com',
    'depends': ['base'],
    'init_xml': [],
    'update_xml': [
        'wiki_view.xml',
        'data/wiki_quickstart.xml',
        'data/wiki_main.xml',
        'wizard/wizard_view.xml',
        'security/ir.model.access.csv'
    ],
    'demo_xml': ['data/wiki_faq.xml'],
    'installable': True,
    'active': False,
    'certificate': '0086363630317',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
