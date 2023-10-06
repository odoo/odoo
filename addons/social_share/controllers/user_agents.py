"""Dictionary associating a social media to the name of the useragent of its opengraph crawler.

Sourced from: https://github.com/monperrus/crawler-user-agents
"""

NETWORK_TO_AGENT = {
    'facebook': [
        'Facebot',
        'facebookexternalhit'
    ],
    'twitter': [
        'Twitterbot',
    ],
    'linkedin': [
        'LinkedInBot',
    ],
    'whatsapp': [
        'WhatsApp',
    ],
    'pinterest': [
        'Pinterest',
        'Pinterestbot'
    ]
}
