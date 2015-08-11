{
    'name': 'Mailing List Archive',
    'category': 'Website',
    'summary': '',
    'version': '1.0',
    'description': """
OpenERP Mail Group : Mailing List Archives
==========================================

        """,
    'depends': ['website_mail'],
    'data': [
        'views/website_mail_channel.xml',
        'views/snippets.xml',
    ],
    'qweb': [],
    'installable': True,
}
