{
    'name': 'Website Instantclick',
    'category': 'Website',
    'summary': 'Preloads and speeds up website on public browsing of the website using Instantclick.',
    'version': '1.0',
    'description': """
Preloads data on anonymous mode of website
==========================================

        """,
    'author': 'OpenERP SA',
    'depends': ['website'],
    'installable': True,
    'data': [
        'views/website_instantclick.xml',
    ],
}
