# -*- coding: utf-8 -*-
{
    'name': 'Twitter Wall',
    'category': 'Website',
    'summary': 'Pretty Way to Display Tweets for Event',
    'version': '1.0',
    'description': """
Display your social media to large screen
=========================================

Turn your event into an interactive experience by letting everybody post messages and photos to your Twitter wall. Connect with the crowd and build a personal relationship with attendees.

 * Create Live twitter walls for event
 * No complex moderation needed, You can display tweets just by posting or re-tweeting from twitter even using twitter's mobile app.
 * Customize your live view with help of various options.
 * Auto Storify view after event is over.
""",
    'author': 'Odoo S.A.',
    'depends': ['website'],
    'website': 'https://www.odoo.com',
    'data': [
        'data/website_twitter_wall_data.xml',
        'security/ir.model.access.csv',
        'views/snippets.xml',
        'views/website_twitter_wall_templates.xml',
        'views/website_twitter_wall_views.xml',
    ],
    'installable': True,
}
