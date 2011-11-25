{
    "name": "web Dashboard",
    "category" : "Hidden",
    "description":'Openerp web Dashboard view',
    "version": "2.0",
    "depends": ['web'],
    "js": [
        'static/src/js/dashboard.js'
    ],
    "css": ['static/src/css/dashboard.css'],
    'qweb' : [
        "static/src/xml/*.xml",
    ],
    'active': True
}
