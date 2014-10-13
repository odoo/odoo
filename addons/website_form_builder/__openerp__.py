{
    'name': 'Website Form Builder',
    'category': 'Website',
    'summary': 'Build your contact form and link it to the database',
    'version': '1.0',
    'description': """
OpenERP Contact Form
====================

        """,
    'author': 'OpenERP SA',
    'depends': ['website'],
    'data': [
        'views/snippets.xml',
        'security/ir.model.access.csv',
        'views/templates.xml',
        'data/website_form_mail.xml'
    ],
    'qweb': [
        'static/src/xml/website.form.editor.wizard.template.xml'
    ],
    'installable': True,
    'auto_install': False,
}
