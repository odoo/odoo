{
    "name" : "Base Kanban",
    "category" : "Hidden",
    "description":'Openerp web kanban view',
    "version" : "2.0",
    "depends" : ["web"],
    "js": [
        "static/src/js/kanban.js"
    ],
    "css": [
        "static/src/css/kanban.css"
    ],
    'qweb' : [
        "static/src/xml/*.xml",
    ],
    'active': True
}
