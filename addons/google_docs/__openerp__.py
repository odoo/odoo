{
    'name': 'Google Docs integration',
    'version': '0.2',
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'category': 'Tools',
    ''' 'data': [
        'google_docs.xml'
    ],'''
    'installable': True,
    'auto_install': False,
    'web': True,
    'js': ['static/src/js/gdocs.js'],
    'qweb' : [
        "static/src/xml/gdocs.xml",
    ],
    'update_xml': [
        'res_config_user_view.xml'
    ],
    'depends': ['google_base_account'],
    'description': 'Module to attach a google document to any model.'
}
