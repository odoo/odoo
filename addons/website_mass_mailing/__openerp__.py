{
    'name': 'Website Mass Mailing Campaigns',
    'description': """
Add a snippet in the website builder to subscribe a mass_mailing list
    """,
    'version': '1.0',
    'category': 'Marketing',
    'depends': ['website', 'mass_mailing'],
    'data': [
        'views/website_mass_mailing.xml',
        'views/unsubscribe.xml',
        'views/snippets.xml',
    ],
    'auto_install': True,
}
