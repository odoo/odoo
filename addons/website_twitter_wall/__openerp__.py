# -*- coding: utf-8 -*-
{
    'name': 'Twitter Wall',
    'category': 'Website',
    'summary': 'Pretty Way to Display Tweets for Event',
    'version': '1.0',
    'description': """
Visualize Tweets
=====================

 * Create wall for event
 * Verify with your twitter account
 * Make storify view of your event
 * Comment on tweet in storify view
 * Display live tweets in different kind of view with mode
 * You display tweets just by posting or re-tweeting from twitter and twitter apps including mobile.
""",
    'author': 'Odoo SA',
    'depends': ['website'],
    'website': 'https://www.odoo.com',
    'data': [
        'views/website_twitter_wall.xml',
        'views/website_twitter_wall_backend.xml',
        'security/ir.model.access.csv',
        'data/website_twitter_wall_data.xml',
    ],
    'installable': True,
}
