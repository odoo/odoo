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
        'data/mail_template_data.xml',
        'views/website_mail_channel.xml',
        'views/snippets.xml',
    ],
    'qweb': [],
    'installable': True,
}
