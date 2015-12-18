{
    'name' : 'IM Bus',
    'version': '1.0',
    'category': 'Hidden',
    'complexity': 'easy',
    'description': "Instant Messaging Bus allow you to send messages to users, in live.",
    'depends': ['base', 'web'],
    'data': [
        'bus_presence_cron.xml',
        'views/bus.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
