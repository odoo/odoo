{
    'name': 'Mailing List Archive',
    'category': 'Website',
    'summary': '',
    'version': '1.0',
    'description': """
OpenERP Mail Group : Mailing List Archives
==========================================

        """,
    'author': 'OpenERP SA',
    'depends': ['website_mail'],
    'data': [
        'views/website_mail_group.xml'
    ],
    'demo': [
        'data/website_mail_group_demo.xml'
    ],
    'qweb': [],
    'installable': True,
}
