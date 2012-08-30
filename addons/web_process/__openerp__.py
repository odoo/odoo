{
    'name': 'Process',
    'version': '2.0',
     'description': """
OpenERP Web process view.
=========================

""",
    'depends': ['web_diagram'],
    'js': [
        'static/lib/dracula/*.js',
        'static/src/js/process.js'
    ],
    'css': [
        'static/src/css/process.css'
    ],
    'qweb': [
        'static/src/xml/*.xml'
    ],
    'auto_install': True
}
