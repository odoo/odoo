{
    'name': 'Mailing List Archive',
    'category': 'Website',
    'summary': '',
    'version': '1.0',
    'description': """
Odoo Mail Group : Mailing List Archives
==========================================

        """,
    'depends': ['website_mail'],
    'data': [
        'views/mail_channel_templates.xml',
        'views/snippets.xml',
    ],
    'qweb': [],
    'installable': True,
}
