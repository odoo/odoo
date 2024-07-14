# -*- coding: utf-8 -*-

{
    'name': 'Twitter Wall',
    'category': 'Website/Website',
    'summary': 'Pretty Way to Display Tweets for Event',
    'description': """
Make Everybody a Part of Your Event
===================================

Turn your event into an interactive experience by letting everybody post to your Twitter Wall. Connect with the crowd and build a personal relationship with attendees.
 * Create Live twitter walls for event
 * No complex moderation needed.
 * Customize your live view with help of various options.
 * Auto Storify view after event is over.
""",
    'license': 'OEEL-1',
    'depends': ['website_twitter'],
    'data': [
        'security/ir.model.access.csv',
        'views/website_twitter_wall_templates.xml',
        'views/website_twitter_wall_views.xml',
        'views/snippets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_twitter_wall/static/src/js/website_twitter_wall.js',
            'website_twitter_wall/static/src/scss/website_twitter_wall.scss',
            'website_twitter_wall/static/src/xml/website_twitter_wall_tweet.xml',
        ],
    }
}
