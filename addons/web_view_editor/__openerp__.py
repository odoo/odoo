{
    "name": "View Editor",
    "category": "Hidden",
    "description":
        """
OpenERP Web to edit views.
==========================

        """,
    "version": "2.0",
    "depends":['web'],
    "js": ["static/src/js/view_editor.js"],
    "css": ['static/src/css/view_editor.css'],
    "qweb": ['static/src/xml/view_editor.xml'],
    'auto_install': True,
}
