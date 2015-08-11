
{
    'name': 'Public Projects',
    'category': 'Website',
    'summary': 'Publish Your Public Projects',
    'version': '1.0',
    'description': """
OpenERP Projects
================

        """,
    'depends': ['website_mail', 'project'],
    'data': [
        'views/website_project.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}
