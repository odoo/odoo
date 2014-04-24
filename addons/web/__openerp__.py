{
    'name': 'Web',
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
OpenERP Web core module.
========================

This module provides the core of the OpenERP Web Client.
        """,
    'depends': ['base'],
    'auto_install': True,
    'data': [
        'views/webclient_templates.xml',
    ],
    'qweb' : [
        "static/src/xml/*.xml",
    ],
    'test': [
        "static/test/testing.js",
        "static/test/framework.js",
        "static/test/registry.js",
        "static/test/form.js",
        "static/test/data.js",
        "static/test/list-utils.js",
        "static/test/formats.js",
        "static/test/rpc-misordered.js",
        "static/test/evals.js",
        "static/test/search.js",
        "static/test/list.js",
        "static/test/list-editable.js",
        "static/test/mutex.js"
    ],
}
