{
    'name': 'Mailing List Archive',
    'category': 'Website',
    'summary': '',
    'version': '1.0',
    'description': """
OpenERP Mail Group : Mailing List Archive
==================

        """,
    'author': 'OpenERP SA',
    'depends': ['website','mail'],
    'data': [
        'views/website_mail_group.xml',
        'views/website_mail_group_backend.xml',
        'data/website_mail_group_data.xml',
        'security/website_mail_group.xml',
    ],
    'demo': [
        'data/website_mail_group_demo.xml'
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}
