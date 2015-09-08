{
    'name': 'Website Form Editor',
    'category': 'Website',
    'summary': 'Build custom web forms using the website builder',
    'version': '1.0',
    'description': """
Odoo Form Editor
====================

Allows you to build web forms on the website using the website builder.
        """,
    'depends': ['website_form'],
    'data': [
        'views/assets.xml',
        'views/snippets.xml',
        'views/ir_model_view.xml',
        'views/snippet_options.xml',
        'data/website_form_mail.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'OEEL-1',
}
