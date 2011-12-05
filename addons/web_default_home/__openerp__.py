{
    "name": "web Default Home",
    "category" : "Hidden",
    "version": "2.0",
    "depends": ['web'],
    "js": [
        'static/src/js/default_home.js'
    ],
    "css": ['static/src/css/default_home.css'],
    'qweb' : [
        "static/src/xml/*.xml",
    ],
    'active': True
}
