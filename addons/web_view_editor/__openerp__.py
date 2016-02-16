{
    'name': 'View Editor',
    'category': 'Hidden',
    'description': """
Odoo Web to edit views.
==========================

        """,
    'version': '2.0',
    'depends':['web'],
    'data' : [
        'views/web_view_editor.xml',
    ],
    'auto_install': True,
}
