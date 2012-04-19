{
    "name": "web_etherpad",
    "category" : "Hidden",
    "description":'Openerp web Etherpad Widget',
    "version": "2.0",
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'data': [
        'res_company.xml'
    ],
    "depends": ['base','web'],
    'qweb' : ['static/src/xml/etherpad.xml'],
    "css": [],
    "js": ['static/src/js/web_etherpad.js'],
    "auto_install": False,
}
